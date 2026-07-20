"""Generate the products dimension table (500 rows)."""

import numpy as np
import pandas as pd
from faker import Faker


# Realistic product name prefixes by subcategory
PRODUCT_PREFIXES = {
    "headphones": ["Wireless", "Noise-Canceling", "Sport", "Studio", "Budget"],
    "laptops": ["UltraBook", "ProBook", "GameStation", "ChromeBook", "WorkStation"],
    "cameras": ["SnapShot", "ProLens", "ActionCam", "MirrorLess", "CompactZoom"],
    "tablets": ["SlimTab", "ProTab", "MiniTab", "StudyTab", "DrawPad"],
    "accessories": ["TechGrip", "PowerBank", "CableKit", "ScreenGuard", "DockStation"],
    "speakers": ["SoundBlast", "MiniSpeaker", "PartyBox", "DeskTone", "PortaSound"],
    "bedding": ["DreamSoft", "CoolSleep", "LuxComfort", "CloudRest", "EcoSleep"],
    "kitchen": ["ChefPro", "QuickMix", "SmartBrew", "FreshKeep", "SliceMaster"],
    "storage": ["SpaceSaver", "StackBox", "TidyBin", "ShelfMax", "OrgPro"],
    "decor": ["ArtWall", "CozyGlow", "ModernVase", "FrameSet", "AccentPiece"],
    "cleaning": ["SparkleClean", "MopPro", "DustAway", "FreshAir", "SteamMax"],
    "lighting": ["BrightLED", "AmbientGlow", "DeskLamp", "SmartBulb", "FloorLight"],
    "tops": ["ClassicTee", "ComfortFit", "UrbanStyle", "ActiveWear", "LayerUp"],
    "pants": ["FlexFit", "SlimCut", "ComfyJog", "WorkPant", "StretchDenim"],
    "dresses": ["ElegantFlow", "CasualChic", "SummerBreeze", "CocktailHour", "DayDress"],
    "outerwear": ["StormShield", "LightLayer", "PufferWarm", "WindBreak", "RainReady"],
    "shoes": ["StrideMax", "ComfortStep", "TrailRun", "CasualKick", "DressWalk"],
    "skincare": ["GlowSerum", "HydraBoost", "ClearSkin", "AgeLess", "SunShield"],
    "makeup": ["TrueColor", "LastAll", "NaturalGlow", "BoldLook", "FlawlessBase"],
    "haircare": ["SilkShine", "VolumeBoost", "RepairPro", "CurlDefine", "ScalpCare"],
    "fragrance": ["EauFresh", "NightBloom", "OceanBreeze", "WoodNote", "CityPulse"],
    "tools": ["PrecisionSet", "BeautyKit", "ProBrush", "TravelEssentials", "StylingPro"],
    "supplements": ["VitaBoost", "DailyWell", "PowerBlend", "PureOmega", "ImmunePlus"],
    "running_shoes": ["SpeedStride", "TrailBlazer", "MarathonPro", "DailyRun", "LightFoot"],
    "fitness": ["IronGrip", "FlexBand", "PowerMat", "GymSet", "BalancePro"],
    "outdoor": ["TrailPack", "CampEssential", "HikeReady", "NatureGear", "SummitPro"],
    "team_sports": ["ProBall", "GameReady", "TeamGear", "FieldPro", "CourtKing"],
    "cycling": ["PedalPro", "RoadRider", "BikeKit", "CycleSafe", "SpeedWheel"],
    "yoga": ["ZenMat", "FlowBlock", "PeaceStrap", "MindfulKit", "BalanceSet"],
    "fiction": ["The Last", "Beyond the", "Shadow of", "The Silent", "A Thousand"],
    "nonfiction": ["The Truth About", "Inside the", "How We", "Rethinking", "The Art of"],
    "business": ["The Lean", "Zero to", "Scale Up", "The Strategy", "Profit First"],
    "tech": ["Code Complete", "Deep Learning", "The Algorithm", "Data Driven", "Build and"],
    "self_help": ["Atomic", "The Power of", "Mindset", "The 7", "Think and"],
    "cooking": ["The Complete", "Simple and", "One Pan", "Plant Based", "The Ultimate"],
}

PRODUCT_SUFFIXES = {
    "headphones": ["Pro", "Elite", "Max", "Air", "SE", "X"],
    "laptops": ["14", "15 Pro", "Air", "Ultra", "S"],
    "cameras": ["Mark II", "X100", "Pro", "Mini", "4K"],
    "tablets": ["10", "Pro 12", "Mini", "Air", "SE"],
    "accessories": ["Kit", "Pack", "Set", "Pro", "Plus"],
    "speakers": ["360", "Mini", "Pro", "XL", "Go"],
}


def generate(config: dict, rng: np.random.Generator) -> pd.DataFrame:
    cfg = config["products"]
    n = cfg["n_products"]
    fake = Faker()
    Faker.seed(int(rng.integers(0, 2**31)))

    # Assign categories based on distribution
    categories = list(cfg["categories"].keys())
    cat_probs = list(cfg["categories"].values())
    product_categories = rng.choice(categories, size=n, p=cat_probs)

    # Assign subcategories
    subcats_map = cfg["subcategories"]
    product_subcategories = []
    for cat in product_categories:
        subs = subcats_map[cat]
        product_subcategories.append(rng.choice(subs))

    # Generate prices (lognormal)
    mu = cfg["price_lognormal_mu"]
    sigma = cfg["price_lognormal_sigma"]
    raw_prices = rng.lognormal(mu, sigma, size=n)
    prices = np.clip(raw_prices, cfg["price_range"][0], cfg["price_range"][1])
    prices = np.round(prices, 2)

    # Cost = 40-70% of price
    margins = rng.uniform(cfg["cost_margin_range"][0], cfg["cost_margin_range"][1], size=n)
    costs = np.round(prices * margins, 2)

    # Plus eligible
    is_plus = rng.random(n) < cfg["plus_eligible_pct"]

    # Generate product names
    names = []
    used_names = set()
    for i in range(n):
        subcat = product_subcategories[i]
        prefixes = PRODUCT_PREFIXES.get(subcat, ["Premium", "Classic", "Modern", "Basic", "Pro"])
        prefix = rng.choice(prefixes)
        suffixes = PRODUCT_SUFFIXES.get(subcat, ["", "Pro", "Plus", "Max", "SE", "V2"])
        suffix = rng.choice(suffixes)
        name = f"{prefix} {subcat.replace('_', ' ').title()} {suffix}".strip()
        # Ensure uniqueness
        while name in used_names:
            name = f"{name} {rng.integers(1, 100)}"
        used_names.add(name)
        names.append(name)

    df = pd.DataFrame({
        "product_id": np.arange(1, n + 1),
        "product_name": names,
        "category": product_categories,
        "subcategory": product_subcategories,
        "price": prices,
        "cost": costs,
        "is_plus_eligible": is_plus,
    })

    return df
