/* @template
name: 品类交叉（目标品类新老客 × 是否历史下过其他品类）
scene: 看目标品类的下单用户里，"当周新客/老客"× "历史是否下过其他兴趣品类订单"四象限分布，用于品类间用户重叠 / 跨品类导流机会评估
params:
  required:
    - target_cate_type: 目标品类名（如 '骑行'）
    - order_full_table: 已按 cate_first_type 打标的订单快照表（含 order_id / user_id / pay_dt / cate_first_type，'target_cate_type' 和 '其他' 两类）
    - start_dt: 时间窗起始
    - end_dt: 时间窗结束
validated:
  - case: 骑行 × 其他兴趣品类交叉（2026-03-02 ~ 2026-06-14）
  - run_at: 2026-06-25
  - source_sql: /Users/zz/Desktop/测试代码/空间盘点/兴趣/骑行/现状/和消费电子的交叉.sql
notes:
  - 需要预先准备 order_full_table：包含所有目标品类 + 其他品类的订单快照，并用 cate_first_type 字段区分（值可为目标品类名或 '其他'）
  - 输出周粒度（周一日期），业务方通常用来看 4 类用户占比走势
business_statement:
  scene_desc: 看 X 品类近 Y 天，当周下单用户在"品类内新老客 × 历史是否下过其他兴趣单"上的四象限分布
  who: 目标品类当周下单用户（uid × pay_week 粒度）
  metric_desc: 每周 × 4 类用户身份的用户数、历史下过其他品类的订单量
  hidden_assumptions:
    - 新老客判定基于目标品类内的 first_pay_week（本周 = 新客，本周之前 = 老客）
    - 历史其他品类订单口径：截至当周周一之前，cate_first_type='其他' 的所有订单
    - 周口径：date_sub(next_day(pay_dt, 'MO'), 7) 转周一日期
  source:
    - ${order_full_table}（需上游已准备好，包含目标品类 + 其他品类订单）
    - hdp_zhuanzhuan_dm_global.dm_trade_order_detail_1d（提取实际支付订单）
*/

-- @lifecycle hdp_zhuanzhuan_dm_global.dm_trade_order_detail_1d=permanent

WITH uid_first_week AS ( -- UID 在各品类下的首销周
    SELECT
        cate_first_type,
        user_id,
        MIN(pay_dt) AS first_pay_dt,
        date_sub(next_day(MIN(pay_dt), 'MO'), 7) AS first_pay_week
    FROM ${order_full_table}
    GROUP BY cate_first_type, user_id
),

pay_order_uid_detail AS ( -- 支付订单 UID × 周粒度
    SELECT
        b.cate_first_type,
        date_sub(next_day(to_date(a.dt), 'MO'), 7) AS pay_week,
        a.uid AS user_id,
        COUNT(DISTINCT a.order_id) AS pay_order_cnt
    FROM hdp_zhuanzhuan_dm_global.dm_trade_order_detail_1d a
    JOIN ${order_full_table} b
      ON a.order_id = b.order_id
     AND a.uid = b.user_id
    WHERE a.uid IS NOT NULL
      AND a.dt BETWEEN '${start_dt}' AND '${end_dt}'
    GROUP BY b.cate_first_type,
             date_sub(next_day(to_date(a.dt), 'MO'), 7),
             a.uid
),

pay_order_uid_overall AS ( -- 每周每 UID 每品类订单量
    SELECT
        cate_first_type, pay_week, user_id,
        SUM(pay_order_cnt) AS pay_order_cnt
    FROM pay_order_uid_detail
    GROUP BY cate_first_type, pay_week, user_id
),

overall_result AS ( -- 目标品类订单用户身份
    SELECT
        a.pay_week,
        a.user_id,
        CASE
            WHEN c.first_pay_week = a.pay_week THEN '当周新客'
            WHEN c.first_pay_week < a.pay_week THEN '当周老客'
            ELSE '未知'
        END AS user_type
    FROM pay_order_uid_overall a
    LEFT JOIN uid_first_week c
      ON a.user_id = c.user_id
     AND a.cate_first_type = c.cate_first_type
    WHERE a.cate_first_type = '${target_cate_type}'
),

other_history_result AS ( -- 截至每周，用户是否历史下过其他兴趣单
    SELECT
        cur.pay_week,
        hist.user_id,
        SUM(hist.pay_order_cnt) AS pay_order_cnt_other_history
    FROM (
        SELECT DISTINCT pay_week
        FROM pay_order_uid_overall
        WHERE cate_first_type = '${target_cate_type}'
    ) cur
    JOIN pay_order_uid_overall hist
      ON hist.cate_first_type = '其他'
     AND hist.pay_week < cur.pay_week
    GROUP BY cur.pay_week, hist.user_id
),

user_final AS ( -- 四象限打标
    SELECT
        a.pay_week,
        CASE
            WHEN a.user_type = '当周新客' AND c.user_id IS NOT NULL THEN '${target_cate_type}新客_历史下过其他兴趣单'
            WHEN a.user_type = '当周新客' AND c.user_id IS NULL     THEN '${target_cate_type}新客_历史无其他兴趣单'
            WHEN a.user_type = '当周老客' AND c.user_id IS NOT NULL THEN '${target_cate_type}老客_历史下过其他兴趣单'
            WHEN a.user_type = '当周老客' AND c.user_id IS NULL     THEN '${target_cate_type}老客_历史无其他兴趣单'
            ELSE '未知'
        END AS user_type,
        a.user_id,
        COALESCE(c.pay_order_cnt_other_history, 0) AS pay_order_cnt_other_history
    FROM overall_result a
    LEFT JOIN other_history_result c
      ON a.pay_week = c.pay_week
     AND a.user_id = c.user_id
)

SELECT
    pay_week,
    user_type,
    COUNT(DISTINCT user_id) AS user_cnt,
    SUM(pay_order_cnt_other_history) AS pay_order_cnt_other_history
FROM user_final
GROUP BY pay_week, user_type
ORDER BY pay_week, user_type;
