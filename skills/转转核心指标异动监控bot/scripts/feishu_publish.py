#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
feishu_publish.py — 把分维度分析报告发飞书(docx + 图 + P2P 纯文本)

沿用 lark-cli v1.0.43 两个已知坑(见 memory feedback-larkcli-p2p-send-quirks)：
  1) P2P 必须 --user-id（open_id），不能 --chat-id
  2) --content/--file 不吃绝对路径与 @file；P2P 文本用 --text 内联

用法：
  LARK_CORE_RECEIVERS="ou_5e57..." python feishu_publish.py --md report.md \
      --msg message.txt --charts-dir ~/.claude/visualizations/2026-07-07 --title "核心指标异动·2026-07-07"
  # 只重推 IM（文档已建）：加 --skip-doc --doc-json out.json
退出码：0=文档OK且至少1人推送成功 / 2=文档OK但推送全失败 / 3=文档失败 / 5=收件人空
"""
import argparse, json, os, re, subprocess, sys, time, glob
from datetime import datetime
from pathlib import Path

LARK = 'lark-cli'


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def parse_json(stdout):
    m = re.search(r'\{.*\}', stdout, re.DOTALL)
    if not m: return None
    try: return json.loads(m.group(0))
    except json.JSONDecodeError: return None


def create_doc(md_path: Path, title: str):
    cwd = md_path.parent
    cp = run([LARK, 'docs', '+create', '--api-version', 'v2',
              '--doc-format', 'markdown', '--title', title,
              '--content', f'@{md_path.name}', '--as', 'user'], cwd=str(cwd))
    if cp.returncode != 0:
        raise RuntimeError(f'docs +create rc={cp.returncode}\n{cp.stderr}\n{cp.stdout}')
    js = parse_json(cp.stdout)
    if not js or not js.get('ok'):
        raise RuntimeError(f'docs +create unexpected: {cp.stdout[:400]}')
    data = js.get('data', {}).get('document') or js.get('data', {})
    token = data.get('document_id') or data.get('doc_token') or data.get('token')
    url = data.get('url') or f'https://zhuanspirit.feishu.cn/docx/{token}'
    if not token:
        raise RuntimeError(f'no token: {js}')
    return token, url


def insert_image(doc_token, png: Path, anchor: str = None):
    """插图。给了 anchor 用 --selection-with-ellipsis 精确插到正文该句所在块之后；
    否则追加到文末。返回 True/False。
    lark-cli v1.0.43 坑：--file 只吃 cwd 相对路径，绝对路径报 'unsafe file path'。
    故以 png 所在盘的 ~/.claude 为 cwd、传相对路径运行。"""
    base = Path.home() / '.claude'
    try:
        rel = png.resolve().relative_to(base.resolve())
        file_arg, cwd = str(rel), str(base)
    except ValueError:
        file_arg, cwd = png.name, str(png.parent)
    cmd = [LARK, 'docs', '+media-insert', '--doc', doc_token,
           '--file', file_arg, '--as', 'user']
    if anchor:
        cmd += ['--selection-with-ellipsis', anchor]
    cp = run(cmd, cwd=cwd)
    return cp.returncode == 0 and '"type": "image"' in cp.stdout


IMG_MARK = re.compile(r'<!--\s*IMG:\s*([^|]+?)\s*\|\s*(.+?)\s*-->')


def extract_img_marks(md_text: str):
    """从 md 抽取 <!--IMG:文件名|锚点句--> 标记，返回 [(文件名, 锚点), ...] 并给出去掉标记行的干净 md。"""
    marks = [(m.group(1).strip(), m.group(2).strip()) for m in IMG_MARK.finditer(md_text)]
    clean = IMG_MARK.sub('', md_text)
    # 清掉因删标记留下的纯空行（连续空行压成一个）
    clean = re.sub(r'\n{3,}', '\n\n', clean)
    return marks, clean


def receiver_flag(rid):
    """按前缀判定收件人类型，返回 lark-cli 的目标参数对。
    oc_ 开头＝群聊 → --chat-id；其余(ou_/on_)＝个人 open_id → --user-id。
    群聊必须走 --chat-id，塞 --user-id 会失败（lark-cli v1.0.43）。"""
    if rid.startswith('oc_'):
        return ['--chat-id', rid]
    return ['--user-id', rid]


def push_text(rid, text):
    cp = run([LARK, 'im', '+messages-send', '--as', 'user',
              *receiver_flag(rid), '--msg-type', 'text', '--text', text])
    js = parse_json(cp.stdout) or {}
    ok = cp.returncode == 0 and js.get('ok')
    return {'open_id': rid, 'status': 'ok' if ok else 'failed',
            'error': None if ok else (cp.stderr or cp.stdout)[:400],
            'pushed_at': datetime.now().isoformat(timespec='seconds')}


def upload_image(png: Path):
    """上传一张图到飞书，拿 image_key（供 post 富文本内嵌）。bot 身份。
    lark-cli 坑同 push_image：路径要 cwd 相对+ASCII，故 copy 到临时名再传。"""
    import shutil, uuid
    tmp = Path.cwd() / f'_post_img_{uuid.uuid4().hex[:8]}.png'
    try:
        shutil.copy(str(png), str(tmp))
        cp = run([LARK, 'im', 'images', 'create', '--as', 'bot',
                  '--data', '{"image_type":"message"}', '--file', f'image=./{tmp.name}'])
        js = parse_json(cp.stdout) or {}
        key = (js.get('data') or {}).get('image_key') or js.get('image_key')
        return key
    finally:
        if tmp.exists():
            tmp.unlink()


def build_post_content(clean_md: str, img_marks, charts_dir):
    """把去标记正文按 IMG 标记切段，组装 post content 二维数组：
    文字段落 → {tag:md}，图 → {tag:img,image_key}。返回 content 列表。
    img_marks 顺序即正文中标记出现顺序；charts_dir 下按文件名找图并上传取 key。"""
    content, key_cache = [], {}
    # 用原始 md（带标记）切段，段间插图；标记本身用占位符切
    raw = clean_md  # 这里传入的是“带标记原文”，见 main 里 push_post 分支
    parts = IMG_MARK.split(raw)
    # re.split 带捕获组：[前文, 文件名, 锚点, 中间文, 文件名, 锚点, ...]
    # 先处理首段文字
    idx = 0
    buf = parts[0]
    i = 1
    while i < len(parts):
        fname = parts[i].strip(); i += 2  # 跳过锚点组
        # 输出到目前累计的文字
        seg = re.sub(r'\n{3,}', '\n\n', buf).strip()
        if seg:
            content.append([{'tag': 'md', 'text': seg}])
        # 上传并插图
        png = Path(charts_dir) / fname if charts_dir else None
        if png and png.exists():
            if fname not in key_cache:
                key_cache[fname] = upload_image(png)
            if key_cache[fname]:
                content.append([{'tag': 'img', 'image_key': key_cache[fname]}])
        buf = parts[i] if i < len(parts) else ''
        i += 1
    tail = re.sub(r'\n{3,}', '\n\n', buf).strip()
    if tail:
        content.append([{'tag': 'md', 'text': tail}])
    return content


def push_post(open_id, title, content):
    """发一条 post 富文本消息到 P2P（图文交插，表格用 md 文本、图用 image_key 内嵌）。
    lark-cli v1.0.43 坑：--content 不吃 @file，必须内联 JSON 字符串（见 memory
    feedback-larkcli-p2p-send-quirks）。post 正文体量远小于 75KB 命令行上限，内联安全。"""
    payload = {'zh_cn': {'title': title, 'content': content}}
    content_json = json.dumps(payload, ensure_ascii=False)
    cp = run([LARK, 'im', '+messages-send', '--as', 'bot', *receiver_flag(open_id),
              '--msg-type', 'post', '--content', content_json])
    js = parse_json(cp.stdout) or {}
    ok = cp.returncode == 0 and js.get('ok')
    return {'open_id': open_id, 'status': 'ok' if ok else 'failed', 'kind': 'post',
            'error': None if ok else (cp.stderr or cp.stdout)[:400],
            'pushed_at': datetime.now().isoformat(timespec='seconds')}


def push_image(open_id, png: Path):
    """发一张图片到 P2P。lark-cli 坑：--image(不是--content)、路径必须 cwd 相对+ASCII。
    故先把图 copy 到 cwd 下 ASCII 临时名，用相对路径发，发完清理。"""
    import shutil, uuid
    tmp = Path.cwd() / f'_anomaly_tbl_{uuid.uuid4().hex[:8]}.png'
    try:
        shutil.copy(str(png), str(tmp))
        as_id = 'bot' if open_id.startswith('oc_') else 'user'
        cp = run([LARK, 'im', '+messages-send', '--as', as_id,
                  *receiver_flag(open_id), '--msg-type', 'image',
                  '--image', f'./{tmp.name}'])
        js = parse_json(cp.stdout) or {}
        ok = cp.returncode == 0 and js.get('ok')
        return {'open_id': open_id, 'status': 'ok' if ok else 'failed',
                'error': None if ok else (cp.stderr or cp.stdout)[:400],
                'kind': 'image', 'file': png.name,
                'pushed_at': datetime.now().isoformat(timespec='seconds')}
    finally:
        if tmp.exists():
            tmp.unlink()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--md', required=True)
    ap.add_argument('--msg', required=True)
    ap.add_argument('--charts-dir', default=None)
    ap.add_argument('--title', required=True)
    ap.add_argument('--doc-json', default=None, help='产物 json 落盘路径')
    ap.add_argument('--push-image', default=None,
                    help='P2P 文本后追加发的图(核心指标总表)，多张用逗号分隔，按序追发，绝对/相对路径皆可')
    ap.add_argument('--skip-doc', action='store_true')
    ap.add_argument('--post', action='store_true',
                    help='P2P 用单条 post 富文本图文交插推送：表格转 md 文本、趋势图按 <!--IMG--> 标记内嵌，'
                         '不再单独逐张发图。文档侧行为不变（仍建 docx 并按标记插图）。')
    ap.add_argument('--post-title', default=None, help='post 标题，默认取 --title')
    ap.add_argument('--extra-link', default=None,
                    help='在 post 正文最顶部(标题正下方)插一条可点击链接，格式「显示文本|url」；'
                         '多条用分号;分隔。用于把分品类曝光明细等关联文档链接固定挂在日报开头。')
    ap.add_argument('--post-md', default=None,
                    help='post 富文本正文来源 md（消息版，表格转文字+趋势图内嵌）；'
                         '不传则用 --md。docx 用 --md（详细报告，结构不变），post 用本参数分开。')
    args = ap.parse_args()

    receivers = [r for r in os.environ.get('LARK_CORE_RECEIVERS', '').split() if r.strip()]
    if not receivers:
        # 默认只推钟梦婷 P2P（见 memory）
        receivers = ['ou_5e572adca6deef8ef21c3b18dfade573']
        print('[warn] LARK_CORE_RECEIVERS 空，默认推钟梦婷', file=sys.stderr)

    md_path = Path(args.md); msg_path = Path(args.msg)
    if not md_path.exists() or not msg_path.exists():
        print(f'[err] 缺文件 md={md_path.exists()} msg={msg_path.exists()}', file=sys.stderr)
        return 3
    out_json = Path(args.doc_json) if args.doc_json else md_path.with_suffix('.feishu.json')

    # 抽 <!--IMG:文件名|锚点--> 标记，创建文档用去标记的干净 md（标记本身不进文档）
    raw_md = md_path.read_text(encoding='utf-8')
    img_marks, clean_md = extract_img_marks(raw_md)
    clean_path = md_path
    if img_marks:
        clean_path = md_path.with_name(md_path.stem + '.__clean__.md')
        clean_path.write_text(clean_md, encoding='utf-8')

    doc_token = doc_url = None
    if args.skip_doc and out_json.exists():
        prev = json.loads(out_json.read_text(encoding='utf-8'))
        doc_token, doc_url = prev.get('doc_token'), prev.get('doc_url')
    if not doc_token:
        try:
            doc_token, doc_url = create_doc(clean_path, args.title)
        except RuntimeError as e:
            print(f'[err] doc 创建失败: {e}', file=sys.stderr); return 3
        # 优先按标记把图插到正文对应位置(--selection-with-ellipsis)；无标记则退回文末追加全部图
        charts = args.charts_dir if (args.charts_dir and os.path.isdir(args.charts_dir)) else None
        if img_marks and charts:
            for fname, anchor in img_marks:
                png = Path(charts) / fname
                if not png.exists():
                    print(f'[warn] 图缺失跳过: {png}', file=sys.stderr); continue
                ok = insert_image(doc_token, png, anchor)
                print(f'[img] {fname} @「{anchor[:20]}」-> {"ok" if ok else "FAIL(退文末重试)"}')
                if not ok:
                    insert_image(doc_token, png)  # 锚点没匹配上，兜底追加文末，别丢图
                time.sleep(0.4)
        elif charts:
            for png in sorted(glob.glob(os.path.join(charts, '*.png'))):
                insert_image(doc_token, Path(png)); time.sleep(0.3)
        if clean_path != md_path and clean_path.exists():
            clean_path.unlink()

    pushes, img_pushes = [], []
    if args.post:
        # v8-0711 改点：P2P 单条 post 富文本图文交插——表格转 md 文本、趋势图按 IMG 标记内嵌。
        # post 正文用报告原文（含 <!--IMG--> 标记与 md 表格），不发短文本 .txt、不逐张追发图。
        charts = args.charts_dir if (args.charts_dir and os.path.isdir(args.charts_dir)) else None
        # post 正文默认取消息版（--post-md 优先，否则 --msg）——不是完整报告 --md。
        # --md 只进 docx（详细报告）；post 是"给人看的紧凑消息"，含四段结论+表图+两张趋势图，剔表3/§五。
        if args.post_md and Path(args.post_md).exists():
            post_raw = Path(args.post_md).read_text(encoding='utf-8')
        else:
            post_raw = msg_path.read_text(encoding='utf-8')
        content = build_post_content(post_raw, extract_img_marks(post_raw)[0], charts)
        # 顶部关联链接（标题正下方）：如分品类曝光明细文档，每日随日报固定挂
        if args.extra_link:
            head = []
            for seg in args.extra_link.split(';'):
                seg = seg.strip()
                if not seg or '|' not in seg:
                    continue
                txt, href = seg.split('|', 1)
                head.append([{'tag': 'a', 'text': txt.strip(), 'href': href.strip()}])
            content[0:0] = head
        if doc_url:
            content.append([{'tag': 'text', 'text': ''},
                            {'tag': 'a', 'text': '📄 查看完整报告文档', 'href': doc_url}])
        title = args.post_title or args.title
        for oid in receivers:
            r = push_post(oid, title, content); pushes.append(r)
            print(f'[push-post] {oid} -> {r["status"]}'); time.sleep(0.5)
    else:
        text = msg_path.read_text(encoding='utf-8')
        if doc_url and doc_url not in text:
            text = text.rstrip() + f'\n\n📄 完整报告：{doc_url}'
        for oid in receivers:
            r = push_text(oid, text); pushes.append(r)
            print(f'[push] {oid} -> {r["status"]}'); time.sleep(0.5)

        # 核心指标总表图（v5-0711 改点1：表1效率 + 表2流量，多张按序追发）
        # 文本推成功后，同一 P2P 依次追发每张表图
        pngs = [Path(p.strip()) for p in args.push_image.split(',') if p.strip()] if args.push_image else []
        for png in pngs:
            if not png.exists():
                print(f'[warn] push-image 缺失跳过: {png}', file=sys.stderr); continue
            for oid in receivers:
                ir = push_image(oid, png); img_pushes.append(ir)
                print(f'[push-img] {png.name} -> {oid} -> {ir["status"]}'); time.sleep(0.5)

    payload = {'doc_url': doc_url, 'doc_token': doc_token,
               'uploaded_at': datetime.now().isoformat(timespec='seconds'),
               'im_push': pushes, 'im_push_image': img_pushes}
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'[done] {out_json}  doc={doc_url}')
    return 0 if any(p['status'] == 'ok' for p in pushes) else 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f'[feishu_publish] internal error: {e}', file=sys.stderr); sys.exit(4)
