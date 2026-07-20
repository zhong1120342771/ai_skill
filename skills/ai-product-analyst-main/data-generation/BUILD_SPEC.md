# NovaMart Dataset Build Spec

## What This Document Is

A complete, detailed specification for building the NovaMart synthetic datasets. Everything needed to implement — database schema, generation logic, embedded data stories, data quality landmines, scripts, agents, verification queries, and build order — is defined here. No implementation decisions should need to be made outside this document.

---

## 1. Project Overview

### 1.1 Purpose
The "AI Analytics for Builders" course needs two synthetic datasets that learners use throughout Weeks 2-5 for hands-on analysis. The datasets must:
- Support every practice exercise, AI demo, and capstone milestone in the course outline
- Embed 6 specific analytical stories (Simpson's paradox, power user fallacy, etc.) that learners discover through investigation
- Be realistic enough that SQL queries, funnel analyses, and statistical tests produce meaningful results
- Be deterministic (seeded) so all learners get identical data

### 1.2 Product Scenario
**NovaMart** — a mid-stage e-commerce marketplace (Amazon-like) with:
- A delivery membership program ("NovaMart Plus")
- Multi-platform: web, iOS, Android
- Multi-channel acquisition: organic, paid search, social, referral, email, TikTok ads
- ~50,000 users, 12 months of data (Jan-Dec 2024)
- ~3-5M behavioral events

### 1.3 Two Datasets

| Dataset | Purpose | Time Window | Data Quality | Analytical Stories |
|---------|---------|-------------|--------------|-------------------|
| **Practice** | Lesson walkthroughs, AI demos | Jan-Dec 2024 | Clean, fully documented | 6 embedded stories (see Section 4) |
| **Capstone** | Homework, capstone project | Jan-Dec 2023 | Has data quality landmines | 4 different stories (see Section 5) |

Both share the same schema. The capstone dataset has structural modifications and data quality issues that learners must discover and fix.

### 1.4 Export Formats
- **CSV** — one file per table, in `data/practice/` and `data/capstone/`
- **DuckDB** — single `.duckdb` database file per dataset for SQL querying

---

## 2. Database Schema

12 tables total: 4 dimension tables, 8 fact/transactional tables, plus 1 helper table.

### 2.1 Dimension Tables

#### `users` — One row per registered user (~50,000 rows)

| Column | Type | Description | Values / Distribution |
|--------|------|-------------|----------------------|
| user_id | INTEGER PK | Unique user ID | 1-50000 |
| signup_date | DATE | Account creation date | Jan 1 - Dec 31, 2024; slight upward trend |
| signup_timestamp | TIMESTAMP | Account creation timestamp | Random time-of-day on signup_date |
| acquisition_channel | TEXT | How user found NovaMart | organic (30%), paid_search (25%), social (15%), referral (10%), email (10%), tiktok_ads (10% — but 0% before Jun 1) |
| country | TEXT | User country | US (65%), UK (12%), CA (8%), DE (7%), AU (5%), other (3%) |
| device_primary | TEXT | Primary device at signup | web (40%), ios (35%), android (25%) |
| age_bucket | TEXT | Age range | 18-24 (15%), 25-34 (30%), 35-44 (25%), 45-54 (18%), 55+ (12%) |
| gender | TEXT | Gender | M (48%), F (47%), other (3%), unknown (2%) |

**Special logic for acquisition_channel:**
- Before Jun 1, 2024: tiktok_ads share is 0%, redistributed proportionally to other channels
- Jun 1 onward: tiktok_ads gets 10% of signups (supporting Story 2: Activation Drop)
- This means pre-June channels have slightly higher shares, post-June they lose share to TikTok

**Signup curve:** Linear growth — ~110 signups/day in Jan, ~165 signups/day in Dec (approximately).

#### `products` — One row per SKU (500 rows)

| Column | Type | Description | Values / Distribution |
|--------|------|-------------|----------------------|
| product_id | INTEGER PK | Unique product ID | 1-500 |
| product_name | TEXT | Product name | Generated names (e.g., "Wireless Headphones Pro") |
| category | TEXT | Product category | electronics (20%), home (20%), clothing (25%), beauty (15%), sports (10%), books (10%) |
| subcategory | TEXT | Product subcategory | Category-appropriate (e.g., electronics → headphones, laptops, cameras, etc.) |
| price | DECIMAL(10,2) | Retail price in USD | $5.99-$499.99, lognormal distribution (median ~$35) |
| cost | DECIMAL(10,2) | Unit cost | 40-70% of price (varies by category) |
| is_plus_eligible | BOOLEAN | Plus free shipping eligible? | 80% true |

**Subcategory mapping:**
- electronics: headphones, laptops, cameras, tablets, accessories, speakers
- home: bedding, kitchen, storage, decor, cleaning, lighting
- clothing: tops, pants, dresses, outerwear, shoes, accessories
- beauty: skincare, makeup, haircare, fragrance, tools, supplements
- sports: running_shoes, fitness, outdoor, team_sports, cycling, yoga
- books: fiction, nonfiction, business, tech, self_help, cooking

#### `promotions` — One row per promotion (5 rows)

| Column | Type | Description |
|--------|------|-------------|
| promo_id | INTEGER PK | 1-5 |
| promo_name | TEXT | Human-readable name |
| promo_type | TEXT | percentage_off, free_shipping, bogo |
| discount_pct | DECIMAL(5,2) | 0.10-0.25 |
| start_date | DATE | Promo start |
| end_date | DATE | Promo end |
| target_segment | TEXT | all, plus_members, new_users |

**Specific promotions:**

| promo_id | name | type | discount | start | end | target |
|----------|------|------|----------|-------|-----|--------|
| 1 | Summer Sale | percentage_off | 0.15 | 2024-07-01 | 2024-07-14 | all |
| 2 | Back to School | percentage_off | 0.10 | 2024-08-15 | 2024-08-31 | all |
| 3 | Black Friday | percentage_off | 0.25 | 2024-11-25 | 2024-12-01 | all |
| 4 | Holiday Sale | percentage_off | 0.20 | 2024-12-15 | 2024-12-31 | all |
| 5 | Welcome10 | percentage_off | 0.10 | 2024-01-01 | 2024-12-31 | new_users |

#### `experiments` — One row per experiment definition (2 rows)

| Column | Type | Description |
|--------|------|-------------|
| experiment_id | INTEGER PK | 1-2 |
| experiment_name | TEXT | Machine-readable name |
| hypothesis | TEXT | Testable hypothesis statement |
| primary_metric | TEXT | What we're measuring |
| guardrail_metrics | TEXT | Comma-separated guardrail metrics |
| start_date | DATE | Experiment start |
| end_date | DATE | Experiment end |
| status | TEXT | completed |

**Specific experiments:**

| experiment_id | name | hypothesis | primary_metric | guardrails | start | end |
|---------------|------|-----------|----------------|------------|-------|-----|
| 1 | save_for_later_visibility | "Increasing visibility of Save for Later will increase 30-day purchase rate by 15%" | purchase_rate | aov,support_tickets,page_load | 2024-08-01 | 2024-09-30 |
| 2 | checkout_redesign | "Simplified mobile checkout will increase mobile checkout conversion by 10%" | checkout_conversion | aov,support_tickets,page_load | 2024-11-20 | 2024-12-31 |

### 2.2 Fact / Transactional Tables

#### `events` — One row per behavioral event (~3-5M rows)

| Column | Type | Description | Values |
|--------|------|-------------|--------|
| event_id | INTEGER PK | Unique event ID | Auto-increment |
| user_id | INTEGER FK | → users.user_id | |
| session_id | TEXT | Session grouping key | Format: "s_{user_id}_{session_counter}" |
| event_timestamp | TIMESTAMP | When event occurred | Within session time window |
| event_date | DATE | Date (for easy grouping) | Derived from timestamp |
| event_type | TEXT | Event type | See list below |
| device | TEXT | Device used | web, ios, android |
| product_id | INTEGER FK nullable | → products.product_id | For product-related events |
| page_url | TEXT nullable | Page URL | For page_view events |
| search_query | TEXT nullable | Search query | For search events |
| app_version | TEXT nullable | App version | For mobile events |

**Event types and their relative frequencies within a session:**
- `page_view` — 35% of events
- `search` — 10%
- `product_view` — 20%
- `add_to_cart` — 8%
- `remove_from_cart` — 2%
- `checkout_started` — 4%
- `payment_attempted` — 3%
- `purchase_complete` — 2.5%
- `save_for_later` — 3%
- `app_open` — 5% (mobile only)
- `signup` — 1% (once per user)
- `login` — 6.5%

**Funnel conversion rates (sequential, session-level):**
- product_view → add_to_cart: 25%
- add_to_cart → checkout_started: 55%
- checkout_started → payment_attempted: 80%
- payment_attempted → purchase_complete: 90%
- **Mobile penalty:** mobile converts at 60% of desktop rate at checkout_started → payment_attempted and payment_attempted → purchase_complete steps

**App version logic:**
- Web events: app_version is NULL
- iOS events: rotating versions — "2.1.0" (Jan-Mar), "2.2.0" (Apr-May), "2.3.0" (Jun only — the buggy version), "2.4.0" (Jul-Dec)
- Android events: "3.1.0" (Jan-Jun), "3.2.0" (Jul-Dec)

#### `sessions` — One row per user session (~500K-1M rows)

| Column | Type | Description |
|--------|------|-------------|
| session_id | TEXT PK | Matches events.session_id |
| user_id | INTEGER FK | → users.user_id |
| session_start | TIMESTAMP | First event timestamp in session |
| session_end | TIMESTAMP | Last event timestamp in session |
| session_date | DATE | Date of session |
| device | TEXT | web, ios, android |
| landing_page | TEXT | First page_url in session |
| page_views | INTEGER | Count of page_view events |
| events_count | INTEGER | Total events in session |
| had_purchase | BOOLEAN | Did session include purchase_complete? |

**Session logic:**
- Average 4.5 sessions per user per month
- Session duration: mean 12 min, std 8 min (minimum 1 min)
- Events per session: mean 5, std 3 (minimum 1)
- Sessions derived from events (30-min inactivity gap = new session)

#### `orders` — One row per order (~30K-50K rows)

| Column | Type | Description |
|--------|------|-------------|
| order_id | INTEGER PK | Unique order ID |
| user_id | INTEGER FK | → users.user_id |
| order_timestamp | TIMESTAMP | When order placed |
| order_date | DATE | Date of order |
| subtotal | DECIMAL(10,2) | Sum of line items before discount |
| discount_amount | DECIMAL(10,2) | Discount applied |
| shipping_amount | DECIMAL(10,2) | Shipping charge (0 for Plus members) |
| total_amount | DECIMAL(10,2) | Final amount charged |
| status | TEXT | completed (85%), cancelled (10%), returned (5%) |
| promo_id | INTEGER FK nullable | → promotions.promo_id (if promo active during order) |
| is_plus_member_order | BOOLEAN | Was buyer a Plus member at time of order? |
| device | TEXT | Device used to place order |
| session_id | TEXT | Session in which order was placed |

**Order logic:**
- Orders are derived from `purchase_complete` events
- Each purchase_complete event creates one order
- 1-4 items per order (mean 2)
- AOV target: ~$75 (resulting from item prices and quantities)
- Promo orders: apply promo_id if order_date falls within a promo's start/end range and user matches target_segment
- Shipping: $5.99 for non-Plus, $0 for Plus members

#### `order_items` — One row per line item (~60K-120K rows)

| Column | Type | Description |
|--------|------|-------------|
| order_item_id | INTEGER PK | Unique line item ID |
| order_id | INTEGER FK | → orders.order_id |
| product_id | INTEGER FK | → products.product_id |
| quantity | INTEGER | 1-3 (usually 1) |
| unit_price | DECIMAL(10,2) | Price at purchase (may differ from products.price during promos) |
| discount_amount | DECIMAL(10,2) | Line-level discount |
| line_total | DECIMAL(10,2) | quantity * unit_price - discount |

#### `memberships` — One row per membership state change (~12K rows)

| Column | Type | Description |
|--------|------|-------------|
| membership_id | INTEGER PK | Auto-increment |
| user_id | INTEGER FK | → users.user_id |
| plan_type | TEXT | plus_trial, plus_monthly, plus_annual |
| started_at | TIMESTAMP | When state began |
| ended_at | TIMESTAMP nullable | When state ended (NULL = current) |
| status | TEXT | active, cancelled, expired, converted |
| cancel_reason | TEXT nullable | price, not_using, competitor, other |
| is_current | BOOLEAN | Is this the current row? |

**Membership logic:**
- 8% of users start a trial within 30 days of signup
- 45% of trials convert to paid (60% monthly, 40% annual)
- Monthly churn: 5% per month
- Annual churn: ~2% per month (lower because of commitment)
- State transitions: trial → (converted to monthly/annual) or (expired) → active → (cancelled)

#### `support_tickets` — One row per ticket (~25K rows)

| Column | Type | Description |
|--------|------|-------------|
| ticket_id | INTEGER PK | Auto-increment |
| user_id | INTEGER FK | → users.user_id |
| created_at | TIMESTAMP | Ticket creation time |
| created_date | DATE | Ticket creation date |
| category | TEXT | payment_issue (25%), delivery_issue (30%), product_quality (20%), account_issue (15%), membership_issue (5%), other (5%) |
| severity | TEXT | low (40%), medium (35%), high (20%), critical (5%) |
| status | TEXT | open (5%), resolved (75%), closed (20%) |
| resolved_at | TIMESTAMP nullable | Resolution time (NULL if open) |
| device | TEXT nullable | Device where issue occurred |
| app_version | TEXT nullable | For mobile tickets |
| order_id | INTEGER FK nullable | → orders.order_id (for order-related tickets, ~60%) |

**Base rate:** 2.5 tickets per 1,000 active users per day.
**Resolution time:** mean 24 hours, std 12 hours (min 1 hour, max 72 hours).

#### `nps_responses` — One row per survey response (~8K rows)

| Column | Type | Description |
|--------|------|-------------|
| response_id | INTEGER PK | Auto-increment |
| user_id | INTEGER FK | → users.user_id |
| response_date | DATE | Survey date |
| score | INTEGER | 0-10 |
| user_segment | TEXT | free, plus (denormalized) |
| device | TEXT | web, ios, android |
| comment | TEXT nullable | Open-ended feedback (~30% have comments) |

**NPS distribution:**
- Free users: mean 28, std 12 (on 0-100 scale; individual scores 0-10)
- Plus users: mean 52, std 10
- ~2,000 responses per quarter
- Surveys sent randomly to active users

**Score-to-NPS conversion:** Scores 0-6 = detractor, 7-8 = passive, 9-10 = promoter. NPS = %promoter - %detractor, scaled to -100 to +100.

#### `experiment_assignments` — One row per user-experiment assignment (~20K rows)

| Column | Type | Description |
|--------|------|-------------|
| assignment_id | INTEGER PK | Auto-increment |
| experiment_id | INTEGER FK | → experiments.experiment_id |
| user_id | INTEGER FK | → users.user_id |
| variant | TEXT | control, treatment |
| assigned_date | DATE | When assigned |
| first_exposure_date | DATE nullable | When first saw variant |

**Assignment logic:**
- Experiment 1 (save_for_later_visibility): 10,000 users, 50/50 split, Aug-Sep 2024
- Experiment 2 (checkout_redesign): 10,000 mobile users, 50/50 split, Nov 20 - Dec 31 2024
- Random assignment, balanced on key dimensions

### 2.3 Helper Table

#### `calendar` — One row per date (366 rows — 2024 is a leap year)

| Column | Type | Description |
|--------|------|-------------|
| date | DATE PK | Calendar date |
| day_of_week | TEXT | Monday-Sunday |
| is_weekend | BOOLEAN | Sat/Sun |
| month | INTEGER | 1-12 |
| quarter | INTEGER | 1-4 |
| is_holiday | BOOLEAN | Major US shopping holidays |
| holiday_name | TEXT nullable | Name of holiday |

**Holidays to include:**
- New Year's Day (Jan 1), Presidents' Day (Feb 19), Memorial Day (May 27), Independence Day (Jul 4), Labor Day (Sep 2), Columbus Day (Oct 14), Veterans Day (Nov 11), Thanksgiving (Nov 28), Black Friday (Nov 29), Cyber Monday (Dec 2), Christmas Eve (Dec 24), Christmas (Dec 25), New Year's Eve (Dec 31)

---

## 3. Lesson-to-Data Requirements Matrix

Every lesson that requires data, mapped to the tables and columns it uses.

### Week 2 — Setup & First Analysis

| Lesson | What Learner Does | Tables | Key Columns | Story? |
|--------|------------------|--------|-------------|--------|
| 2.6 | Load CSV, explore row counts, columns, summary stats | `support_tickets` | all | No |
| 2.11 | SQL: GROUP BY category, daily volume | `support_tickets` | created_at, category | No |
| 2.12 | Bar chart, date filter, dropdown | `support_tickets` | created_at, category, device | No |
| 2.14 | Full analysis: when did spike start, which categories, which segments, trend chart | `support_tickets`, `users` | created_at, category, device, app_version, user_id | **Story 1** |
| 2.15 | Same analysis in Hex | `support_tickets`, `users` | same as above | **Story 1** |
| 2.18 | First analysis output + analysis design spec | practice dataset | any | No |

### Week 3 — Metrics & Root Cause

| Lesson | What Learner Does | Tables | Key Columns | Story? |
|--------|------------------|--------|-------------|--------|
| 3.4 | Define MAU with edge cases | `events`, `users` | user_id, event_timestamp, event_type | No |
| 3.6 | Build metric tree: Revenue → Users x ARPU → decomposition | `orders`, `order_items`, `users`, `products` | order_value, user_id, product category | No |
| 3.11 | Apply 5 sanity checks to outputs with planted issues | (pre-computed outputs) | — | No |
| 3.15 | Debug checkout funnel | `events`, `users` | event_type funnel steps, device, user_segment | **Story 6** |
| 3.17 | Compare aggregate vs segmented NPS | `nps_responses`, `users`, `memberships` | score, user_segment, response_date | **Story 3** |
| 3.20 | Decompose 20% activation drop | `users`, `orders`, `events` | acquisition_channel, created_at, first_order_at | **Story 2** |
| 3.21 | AI demo of activation drop investigation | same as 3.20 | same | **Story 2** |
| 3.22 | Metric spec + metric tree + guardrails + root cause memo | capstone dataset | varies | Capstone |

### Week 4 — Experimentation & Causal Thinking

| Lesson | What Learner Does | Tables | Key Columns | Story? |
|--------|------------------|--------|-------------|--------|
| 4.8 | Power intuition: can we detect X% with N users? | `users`, `orders` | user counts, baseline rates | No |
| 4.11 | Apply Result Interpretation Tree to scenarios | `experiment_assignments`, `orders`, `events` | variant, conversion metrics | **Story 4** |
| 4.13 | Conversion up 20% but AOV down 15% — net revenue? | `experiment_assignments`, `orders`, `order_items` | variant, conversion, order_value | No |
| 4.17 | Power calc, pre-post, diff-in-diff | `events`, `orders`, `users`, `experiment_assignments`, `promotions` | checkout CVR by device/country, promo dates | **Story 5** |
| 4.18 | AI demo: experiment design + monitoring | same as 4.17 | same | **Stories 4 & 5** |
| 4.19 | Experiment brief OR causal analysis design | capstone dataset | varies | Capstone |

### Week 5 — Storytelling, Influence & Prioritization

| Lesson | What Learner Does | Tables | Key Columns | Story? |
|--------|------------------|--------|-------------|--------|
| 5.4 | Size the mobile checkout gap opportunity | `events`, `orders`, `users` | checkout_started by device, CVR, AOV | **Story 6** |
| 5.6 | Sensitivity: vary improvement from 1pp to 5pp | derived from 5.4 | same | **Story 6** |
| 5.9 | Stack rank 5 opportunities | derived from data | various | No |
| 5.18 | Build sizing models with AI | `events`, `orders`, `users`, `memberships` | conversion rates, revenue, membership | **Story 6** |
| 5.20 | AI demo: size + prioritize + narrative | all tables | various | No |
| 5.21 | Final capstone deliverable | capstone dataset | all | Capstone |

---

## 4. Embedded Data Stories (Practice Dataset)

These are specific patterns embedded in the practice data that learners discover through analytical investigation. Each story has a precise numerical specification.

### Story 1: Support Ticket Spike (Week 2, lessons 2.14-2.15)

**What learner sees:** Support ticket volume suddenly spikes.
**What learner discovers:** iOS app v2.3 introduced a payment processing bug.

**Data specification:**
- **Baseline:** ~40 payment_issue tickets/day (25% of ~160 total/day)
- **Spike period:** Jun 1 - Jun 14, 2024
- **During spike:** payment_issue tickets jump to ~120/day (3x multiplier)
- **Spike is iOS only:** 90% of spike tickets have device='ios' AND app_version='2.3.0'
- **All other categories:** Flat, unchanged during spike period
- **Android and web:** Unaffected
- **After Jun 14:** Returns to baseline (v2.4.0 fixes the bug)

**Discovery path:**
1. Group tickets by date → see spike
2. Group by category → payment_issue dominates the spike
3. Group by device → iOS only
4. Check app_version → v2.3.0

**Verification query:**
```sql
SELECT created_date, category, device,
       COUNT(*) as tickets
FROM support_tickets
WHERE created_date BETWEEN '2024-06-01' AND '2024-06-14'
GROUP BY 1, 2, 3
ORDER BY 1, 4 DESC;
-- Should show payment_issue + ios >> all others
```

### Story 2: Activation Drop / Channel Mix Shift (Week 3, lessons 3.20-3.21)

**What learner sees:** 7-day activation rate drops from ~30% to ~24%.
**What learner discovers:** TikTok ads brought high-volume but low-intent users.

**Data specification:**
- **Activation definition:** User places first order within 7 days of signup
- **Pre-June (Jan-May):** Overall activation ~30%
  - organic: 40%, paid_search: 35%, social: 25%, referral: 45%, email: 30%
  - tiktok_ads: doesn't exist yet
- **Post-June (Jun-Dec):** Overall activation drops to ~24%
  - Within each channel: rates are STABLE or SLIGHTLY IMPROVING (+1-2pp)
  - tiktok_ads: 15% activation rate
  - tiktok_ads grows from 0% to ~30% of signups
  - Mix shift drags aggregate down
- **Math check:** Post-June approximate mix: organic 21%, paid_search 18%, social 11%, referral 7%, email 7%, tiktok_ads 30%, rest ~6%
  - Weighted: 0.21(41) + 0.18(36) + 0.11(26) + 0.07(46) + 0.07(31) + 0.30(15) + 0.06(35) ≈ 8.6 + 6.5 + 2.9 + 3.2 + 2.2 + 4.5 + 2.1 = 30.0...
  - Need to tune so aggregate is clearly ~24%, not 30%. Increase tiktok share or lower its activation rate further.
  - **Revised:** tiktok_ads = 35% of post-June signups, activation = 12%. Other channels lose more share.
  - Weighted: 0.18(41) + 0.15(36) + 0.09(26) + 0.06(46) + 0.06(31) + 0.35(12) + 0.11(35) ≈ 7.4 + 5.4 + 2.3 + 2.8 + 1.9 + 4.2 + 3.9 = 27.9... still a bit high.
  - **Final tuning will happen during generation** — the key constraint is: aggregate drops ~6pp while within-channel rates are stable.

**Discovery path:**
1. Calculate overall activation rate by signup month → see drop starting June
2. Segment by channel → all channels stable
3. Notice tiktok_ads appears in June with high volume
4. TikTok has 12-15% activation vs 25-45% for other channels
5. Conclude: mix shift, not a product problem

**Verification query:**
```sql
WITH activations AS (
  SELECT u.user_id,
         u.acquisition_channel,
         CASE WHEN u.signup_date < '2024-06-01' THEN 'pre' ELSE 'post' END as period,
         CASE WHEN MIN(o.order_date) <= u.signup_date + 7 THEN 1 ELSE 0 END as activated
  FROM users u
  LEFT JOIN orders o ON u.user_id = o.user_id
  GROUP BY 1, 2, 3
)
SELECT period, acquisition_channel,
       COUNT(*) as users,
       AVG(activated) as activation_rate
FROM activations
GROUP BY 1, 2
ORDER BY 1, 3 DESC;
-- Within each channel: rates similar pre/post
-- tiktok_ads: appears only in 'post', low rate
-- Overall 'post' rate < 'pre' rate
```

### Story 3: NPS Simpson's Paradox (Week 3, lesson 3.17)

**What learner sees:** Aggregate NPS drops from 42 to 38 (Q1 → Q2).
**What learner discovers:** Both segments improved, but mix shifted toward more Free user responses.

**Data specification:**
- **Q1:** ~2,000 responses. 40% Free (NPS ~28), 60% Plus (NPS ~52)
  - Aggregate: 0.40(28) + 0.60(52) = 42.4
- **Q2:** ~2,000 responses. 60% Free (NPS ~30), 40% Plus (NPS ~54)
  - Aggregate: 0.60(30) + 0.40(54) = 39.6
- Both Free and Plus improved (+2 each), but aggregate dropped (-2.8)
- Cause: Marketing pushed a feedback campaign to Free users, increasing their response share from 40% → 60%
- Q3 and Q4 can have gradual return to ~50/50 mix

**Implementation:**
- Generate NPS scores from normal distribution, clamped to 0-10
- For Free users: mean score that produces NPS ~28 in Q1, ~30 in Q2
- For Plus users: mean score that produces NPS ~52 in Q1, ~54 in Q2
- Control the Free/Plus mix per quarter

**NPS calculation note:** NPS score (0-10) maps to categories:
- 0-6: Detractor
- 7-8: Passive
- 9-10: Promoter
- NPS = (% Promoter - % Detractor) × 100

To get NPS ~28 for Free users, need a distribution where the promoter-detractor gap ≈ 28 points. This requires careful calibration of the score distribution.

**Approximate target distributions (scores 0-10):**
- Free Q1 (NPS ~28): mean ~6.5, std ~2.5 → ~35% detractors, ~25% passive, ~40% promoters → NPS ≈ 5... too low
- Need to think in terms of the 0-10 score generating the right NPS
- Free users NPS ~28: need ~44% promoter, ~16% detractor → score distribution centered around 7.5 with some spread
- Plus users NPS ~52: need ~60% promoter, ~8% detractor → score distribution centered around 8.5

**Revised approach:** Generate scores directly to hit target NPS values. Use a mixture model or simply control the promoter/passive/detractor percentages directly, then sample individual scores within each bucket.

**Verification query:**
```sql
SELECT
  CASE WHEN response_date <= '2024-03-31' THEN 'Q1'
       WHEN response_date <= '2024-06-30' THEN 'Q2'
       WHEN response_date <= '2024-09-30' THEN 'Q3'
       ELSE 'Q4' END as quarter,
  user_segment,
  COUNT(*) as responses,
  ROUND(100.0 * (
    SUM(CASE WHEN score >= 9 THEN 1 ELSE 0 END) -
    SUM(CASE WHEN score <= 6 THEN 1 ELSE 0 END)
  ) / COUNT(*), 1) as nps
FROM nps_responses
GROUP BY 1, 2
ORDER BY 1, 2;
-- Q1: Free ~28, Plus ~52, aggregate ~42
-- Q2: Free ~30, Plus ~54, aggregate ~39
```

### Story 4: Power User Fallacy (Week 4, lessons 4.11, 4.17-4.18)

**What learner sees:** Users who use "Save for Later" have 3x higher purchase rate.
**What learner discovers:** Selection bias. Experiment shows only ~8% causal lift.

**Data specification:**

**Observational pattern (in general events data):**
- Users who have ≥1 `save_for_later` event: ~45% have a purchase within 30 days
- Users with 0 `save_for_later` events: ~15% have a purchase within 30 days
- Correlation ratio: 3x (45% / 15%)
- Reason: high-intent users self-select into using the feature. They browse more, have more sessions, and are more engaged regardless of save_for_later.

**Experimental pattern (experiment 1: save_for_later_visibility):**
- 10,000 users assigned Aug 1, 2024
- 5,000 control, 5,000 treatment
- Treatment: Save for Later button is more prominent (larger, different color)
- Control: 15.3% 30-day purchase rate
- Treatment: 16.5% 30-day purchase rate
- True lift: ~8% relative (1.2pp absolute)
- Statistically significant but much smaller than the 3x observational correlation

**Confounders to embed:**
- Save_for_later users have 2x more sessions per month
- Save_for_later users have 3x more product_view events
- Save_for_later users are more likely to be Plus members

**Verification queries:**
```sql
-- Observational
SELECT
  CASE WHEN sfl.user_id IS NOT NULL THEN 'used_save_for_later' ELSE 'never_used' END as group,
  COUNT(DISTINCT e.user_id) as users,
  COUNT(DISTINCT CASE WHEN o.order_id IS NOT NULL THEN e.user_id END) as purchasers,
  ROUND(100.0 * COUNT(DISTINCT CASE WHEN o.order_id IS NOT NULL THEN e.user_id END) / COUNT(DISTINCT e.user_id), 1) as purchase_rate
FROM (SELECT DISTINCT user_id FROM events) e
LEFT JOIN (SELECT DISTINCT user_id FROM events WHERE event_type = 'save_for_later') sfl ON e.user_id = sfl.user_id
LEFT JOIN orders o ON e.user_id = o.user_id
GROUP BY 1;
-- Should show ~3x difference

-- Experimental
SELECT ea.variant,
       COUNT(DISTINCT ea.user_id) as users,
       COUNT(DISTINCT o.user_id) as purchasers,
       ROUND(100.0 * COUNT(DISTINCT o.user_id) / COUNT(DISTINCT ea.user_id), 1) as purchase_rate
FROM experiment_assignments ea
LEFT JOIN orders o ON ea.user_id = o.user_id
  AND o.order_date BETWEEN ea.assigned_date AND ea.assigned_date + 30
WHERE ea.experiment_id = 1
GROUP BY 1;
-- Should show ~8% relative lift (15.3% vs 16.5%)
```

### Story 5: Checkout Redesign + Promo Confound (Week 4, lessons 4.17-4.18)

**What learner sees:** Mobile checkout conversion jumped after Nov 20 redesign.
**What learner discovers:** Most of the lift is from Black Friday promo, not the redesign.

**Data specification:**

| Period | Mobile CVR | Desktop CVR | Notes |
|--------|-----------|-------------|-------|
| Pre-redesign (Nov 1-19) | 6.0% | 10.0% | Baseline |
| Redesign only (Nov 20-24) | 6.5% | 10.0% | Redesign effect = +0.5pp |
| Redesign + promo (Nov 25-30) | 9.5% | 13.0% | Promo adds ~3pp to both |
| Post-promo (Dec 2-14) | 6.5% | 10.0% | Promo effect gone, redesign persists |

**Naive pre-post analysis:** (6.0% → 9.5%) = +58% relative lift. Misleading!
**Diff-in-Diff:**
- Mobile change (Nov 20-24 vs Nov 1-19): 6.5% - 6.0% = +0.5pp
- Desktop change (same periods): 10.0% - 10.0% = 0pp
- DiD estimate: 0.5pp — the true redesign effect

**Implementation:**
- Checkout conversion = purchase_complete / checkout_started, per session
- Redesign only affects mobile (experiment 2 assigns mobile users)
- During Black Friday promo (Nov 25 - Dec 1), both mobile and desktop get ~3pp lift
- Desktop serves as the natural control group

**Verification query:**
```sql
WITH checkout_data AS (
  SELECT
    event_date,
    device,
    CASE
      WHEN event_date BETWEEN '2024-11-01' AND '2024-11-19' THEN 'pre'
      WHEN event_date BETWEEN '2024-11-20' AND '2024-11-24' THEN 'redesign_only'
      WHEN event_date BETWEEN '2024-11-25' AND '2024-11-30' THEN 'redesign_plus_promo'
      WHEN event_date BETWEEN '2024-12-02' AND '2024-12-14' THEN 'post_promo'
    END as period,
    COUNT(CASE WHEN event_type = 'checkout_started' THEN 1 END) as checkouts,
    COUNT(CASE WHEN event_type = 'purchase_complete' THEN 1 END) as purchases
  FROM events
  WHERE event_date BETWEEN '2024-11-01' AND '2024-12-14'
    AND device IN ('web', 'ios', 'android')
  GROUP BY 1, 2
)
SELECT period,
       CASE WHEN device = 'web' THEN 'desktop' ELSE 'mobile' END as platform,
       SUM(checkouts) as total_checkouts,
       SUM(purchases) as total_purchases,
       ROUND(100.0 * SUM(purchases) / NULLIF(SUM(checkouts), 0), 1) as cvr
FROM checkout_data
WHERE period IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, 2;
```

### Story 6: Mobile Checkout Gap (Week 5, lessons 5.4, 5.6, 5.18)

**What learner sees:** Mobile checkout conversion is 4pp lower than desktop.
**What learner discovers:** This gap represents a $900K+ annual revenue opportunity.

**Data specification:**
- **Mobile checkout CVR:** ~6% (across iOS + Android)
- **Desktop checkout CVR:** ~10%
- **Gap:** 4 percentage points
- **Monthly mobile checkout_started:** ~50,000
- **Average order value:** ~$75

**Sizing model:**
- Lost conversions/month = 50,000 × 0.04 = 2,000
- Lost revenue/month = 2,000 × $75 = $150,000
- Annual opportunity (full gap close) = $150,000 × 12 = $1,800,000
- Realistic (close half the gap) = $900,000

**Sensitivity analysis inputs:**
- Gap close: 25%, 50%, 75%, 100%
- Conversion improvement: 1pp, 2pp, 3pp, 4pp
- AOV variation: $60, $75, $90

---

## 5. Capstone Dataset Modifications

### 5.1 Structural Differences

| Modification | Details | Lesson Alignment |
|-------------|---------|-----------------|
| **Missing column** | `nps_responses` has no `user_segment` column. Learner must join to `memberships` to determine Free vs Plus. | 3.17 (segmentation) |
| **Incomplete data** | `support_tickets.device` is NULL for 30% of rows (tracking gap in older app versions) | 3.11 (data quality) |
| **Missing table** | No `sessions` table provided. Learner must derive sessions from `events` using 30-min inactivity gap. | 2.14, 3.15 (funnel) |

### 5.2 Data Quality Landmines

| Landmine | Implementation | How to Detect | Lesson |
|----------|---------------|---------------|--------|
| **Duplicate events** | 2% of Android events duplicated (same event_id, same timestamp, same user_id). Created by re-inserting copies of random Android events. | `SELECT event_id, COUNT(*) FROM events GROUP BY event_id HAVING COUNT(*) > 1` | 3.10-3.11 |
| **Missing iOS events** | Zero iOS events for Oct 1-7, 2024. Logging outage. | Time series of iOS event counts shows gap. | 3.10-3.11, 3.20 |
| **Delayed timestamps** | 3% of events have timestamps shifted +7 hours (UTC/PT confusion). | Events at unusual hours (3am-5am), or session durations seem too long. | 3.10-3.11 |
| **Unstitched sessions** | 5% of sessions have broken session_id linkage (anonymous → logged-in transition not joined). Same user appears to have two sessions happening simultaneously. | Multiple session_ids for same user in overlapping time windows. | 3.15 |
| **Orphan orders** | 1% of orders reference user_ids not in the `users` table (deleted accounts). | `SELECT COUNT(*) FROM orders o LEFT JOIN users u ON o.user_id = u.user_id WHERE u.user_id IS NULL` | 3.10 |

### 5.3 Capstone Analytical Stories (Different from Practice)

| Story | Description | Pattern | What Students Find |
|-------|-------------|---------|-------------------|
| **Simpson's Paradox (different)** | Overall conversion rate drops Q2→Q3, but within each acquisition channel it rose. Mix shift toward lower-converting organic traffic (paid budget cut). | Aggregate down, every segment up, organic share increased | Segment by channel, identify mix shift from budget reallocation |
| **Selection Bias (different)** | Users who enable push notifications have 2x retention. Experiment shows notifications improve retention by only 12%. | Observational: 2x. Experimental: 12% relative lift. | Distinguish correlation from causation |
| **Seasonality Trap** | Naive YoY comparison shows "growth" — but it's comparing Dec 2022 (holiday) to Jan 2023 (post-holiday). Must compare Dec-to-Dec or deseasonalize. | Month-to-month "decline" in Jan is actually normal seasonality | Compare same months YoY or deseasonalize |
| **Confounding (different)** | Price drop and UI change shipped same week. Both could explain conversion lift. Need to segment by platform (UI change was mobile-only, price drop was universal). | Use mobile vs desktop as natural experiment | Segment by platform to isolate effects |

---

## 6. Scripts and File Structure

### 6.1 Directory Layout

```
data-generation/
├── BUILD_SPEC.md                  # This document
├── config.yaml                    # All tunable parameters (single source of truth)
├── generate.py                    # Main orchestrator — runs all generators in order
├── requirements.txt               # Python dependencies
├── generators/
│   ├── __init__.py
│   ├── calendar_gen.py            # dim: calendar (366 rows)
│   ├── products.py                # dim: products (500 rows)
│   ├── promotions.py              # dim: promotions (5 rows)
│   ├── experiments.py             # dim: experiments (2 rows)
│   ├── users.py                   # dim: users (50K rows)
│   ├── sessions_and_events.py     # fact: sessions + events (500K-1M + 3-5M rows)
│   ├── orders.py                  # fact: orders + order_items (30-50K + 60-120K)
│   ├── memberships.py             # fact: memberships (~12K rows)
│   ├── support_tickets.py         # fact: support_tickets (~25K rows)
│   ├── nps_responses.py           # fact: nps_responses (~8K rows)
│   └── experiment_assignments.py  # fact: experiment_assignments (~20K rows)
├── stories/
│   ├── __init__.py
│   ├── ticket_spike.py            # Modify support_tickets for Story 1
│   ├── activation_drop.py         # Modify users for Story 2 (TikTok channel)
│   ├── nps_paradox.py             # Modify nps_responses for Story 3
│   ├── power_user_fallacy.py      # Modify events + experiment data for Story 4
│   └── checkout_confound.py       # Modify events for Story 5
├── capstone/
│   ├── __init__.py
│   ├── apply_landmines.py         # Apply data quality issues
│   └── capstone_stories.py        # Generate capstone-specific stories
├── quality_gates.py               # Post-generation validation
├── load_duckdb.py                 # Create .duckdb from CSVs
└── export.py                      # Export DataFrames to CSV files

data/
├── practice/                      # Generated practice CSVs + DuckDB
│   ├── users.csv
│   ├── products.csv
│   ├── promotions.csv
│   ├── experiments.csv
│   ├── events.csv
│   ├── sessions.csv
│   ├── orders.csv
│   ├── order_items.csv
│   ├── memberships.csv
│   ├── support_tickets.csv
│   ├── nps_responses.csv
│   ├── experiment_assignments.csv
│   ├── calendar.csv
│   └── novamart_practice.duckdb
└── capstone/                      # Generated capstone CSVs + DuckDB
    ├── (same files minus sessions.csv)
    ├── (nps_responses.csv without user_segment column)
    └── novamart_capstone.duckdb
```

### 6.2 Script Descriptions

#### `config.yaml`
Single source of truth for all tunable parameters: user counts, distributions, funnel rates, story parameters, date ranges, random seeds. Every magic number in the generators should reference this file. Shape matches what's in the plan (Section 8 below).

#### `generate.py` — Main Orchestrator
- Loads `config.yaml`
- Sets global random seed
- Calls generators in dependency order (see Section 7)
- Calls story injectors to modify generated data
- Calls `export.py` to write CSVs
- Calls capstone modifiers to create capstone variant
- Calls `quality_gates.py` to validate
- Calls `load_duckdb.py` to create database files
- Prints summary statistics and timing

#### Generator Scripts (`generators/`)
Each generator:
- Takes config dict and any dependent DataFrames as input
- Returns one or more pandas DataFrames
- Uses numpy random with config seed for determinism
- Handles its own data validation (column types, nullability)

**Key generators:**

- **`sessions_and_events.py`** — The most complex generator. Must:
  - Generate sessions for each user across their active months
  - Within each session, generate a realistic sequence of events following the funnel
  - Apply mobile checkout penalty
  - Apply app_version logic based on device and date
  - This is the bottleneck for performance (~3-5M rows)

- **`orders.py`** — Derives from purchase_complete events:
  - Each purchase_complete event becomes an order
  - Assigns 1-4 order_items per order
  - Selects products based on category distribution
  - Applies promos if order_date falls in a promo window
  - Calculates subtotal, discount, shipping, total

- **`memberships.py`** — State machine per user:
  - 8% of users start a trial
  - Trial → paid (45%) or expired (55%)
  - Monthly churn applied each month
  - Track state transitions as rows

#### Story Injectors (`stories/`)
Each story script takes generated DataFrames and modifies them in place to embed the analytical pattern. Stories are applied AFTER base generation but BEFORE export.

- **`ticket_spike.py`** — Adds extra payment_issue tickets for iOS v2.3 during Jun 1-14
- **`activation_drop.py`** — Already handled in `users.py` by the TikTok channel launch logic. This script validates the pattern exists and adjusts if needed.
- **`nps_paradox.py`** — Controls the Free/Plus response mix per quarter and adjusts score distributions
- **`power_user_fallacy.py`** — Ensures save_for_later users have correlated higher engagement; ensures experiment results show small effect
- **`checkout_confound.py`** — Adjusts mobile checkout conversion rates around Nov 20 and during Black Friday

#### Capstone Scripts (`capstone/`)
- **`apply_landmines.py`** — Takes the clean practice data, applies all 5 data quality issues
- **`capstone_stories.py`** — Generates the 4 capstone-specific analytical stories

#### `quality_gates.py`
Runs all validation checks (see Section 9). Returns pass/fail for each gate with diagnostic messages.

#### `load_duckdb.py`
Reads CSV files from a directory, creates a DuckDB database, loads all tables, adds primary key and foreign key constraints where possible.

#### `export.py`
Takes dict of DataFrames, writes each to CSV in the specified output directory.

### 6.3 Dependencies

```
# requirements.txt
pandas>=2.0
numpy>=1.24
pyyaml>=6.0
duckdb>=0.9
faker>=20.0        # for generating realistic product names, comments
tqdm>=4.65         # progress bars for long-running generators
```

---

## 7. Generation Order and Dependencies

```
Phase 1 — Independent dimensions (no dependencies, can run in parallel):
  ├── calendar_gen.py      → calendar_df
  ├── products.py          → products_df
  ├── promotions.py        → promotions_df
  └── experiments.py       → experiments_df

Phase 2 — Users (depends on calendar for signup dates):
  └── users.py             → users_df
      (uses calendar for valid dates, applies TikTok channel logic)

Phase 3 — Behavioral data (depends on users, products, calendar):
  └── sessions_and_events.py → sessions_df, events_df
      (generates sessions per user, events per session,
       applies funnel logic, mobile penalty, app versions)

Phase 4 — Derived facts (depend on events/users):
  ├── orders.py            → orders_df, order_items_df
  │   (derives from purchase_complete events)
  ├── memberships.py       → memberships_df
  │   (depends on users, calendar)
  ├── support_tickets.py   → support_tickets_df
  │   (depends on users, orders)
  ├── nps_responses.py     → nps_responses_df
  │   (depends on users, memberships)
  └── experiment_assignments.py → experiment_assignments_df
      (depends on users, experiments)

Phase 5 — Story injection (modifies existing DataFrames):
  ├── ticket_spike.py      → modifies support_tickets_df
  ├── nps_paradox.py       → modifies nps_responses_df
  ├── power_user_fallacy.py → modifies events_df, experiment_assignments_df
  └── checkout_confound.py → modifies events_df

Phase 6 — Export practice dataset:
  └── export.py            → writes CSVs to data/practice/
  └── load_duckdb.py       → creates data/practice/novamart_practice.duckdb

Phase 7 — Generate capstone dataset:
  ├── apply_landmines.py   → modifies copies of DataFrames
  ├── capstone_stories.py  → embeds capstone stories
  └── export.py            → writes CSVs to data/capstone/ (minus sessions, minus nps user_segment)
  └── load_duckdb.py       → creates data/capstone/novamart_capstone.duckdb

Phase 8 — Validation:
  └── quality_gates.py     → validates both datasets
```

**Note on Story 2 (Activation Drop):** This story is primarily implemented in `users.py` (TikTok channel appears Jun 1+) and `sessions_and_events.py` (TikTok users have lower session frequency and purchase intent). The `activation_drop.py` story script validates the pattern and makes adjustments if the aggregate activation rate isn't in the target range.

---

## 8. Config File Shape

```yaml
general:
  time_range: ["2024-01-01", "2024-12-31"]
  random_seed: 42
  practice_output_dir: "data/practice"
  capstone_output_dir: "data/capstone"

users:
  n_users: 50000
  acquisition_channels:
    organic: 0.30
    paid_search: 0.25
    social: 0.15
    referral: 0.10
    email: 0.10
    tiktok_ads: 0.10          # launches 2024-06-01, share ramps up
  tiktok_launch_date: "2024-06-01"
  tiktok_post_launch_share: 0.35  # TikTok's share of signups after launch
  countries:
    US: 0.65
    UK: 0.12
    CA: 0.08
    DE: 0.07
    AU: 0.05
    other: 0.03
  devices:
    web: 0.40
    ios: 0.35
    android: 0.25
  age_buckets:
    "18-24": 0.15
    "25-34": 0.30
    "35-44": 0.25
    "45-54": 0.18
    "55+": 0.12
  gender:
    M: 0.48
    F: 0.47
    other: 0.03
    unknown: 0.02
  signup_curve: "linear_growth"     # ~110/day Jan → ~165/day Dec

products:
  n_products: 500
  categories:
    electronics: 0.20
    home: 0.20
    clothing: 0.25
    beauty: 0.15
    sports: 0.10
    books: 0.10
  price_range: [5.99, 499.99]
  price_distribution: "lognormal"
  price_lognormal_mu: 3.5           # ln($33)
  price_lognormal_sigma: 0.8
  cost_margin_range: [0.40, 0.70]   # cost = 40-70% of price
  plus_eligible_pct: 0.80

sessions:
  avg_sessions_per_user_per_month: 4.5
  session_duration_minutes:
    mean: 12
    std: 8
    min: 1
    max: 60
  events_per_session:
    mean: 5
    std: 3
    min: 1
    max: 25

funnel:
  product_view_to_add_to_cart: 0.25
  add_to_cart_to_checkout: 0.55
  checkout_to_payment: 0.80
  payment_to_purchase: 0.90
  mobile_checkout_penalty: 0.60     # mobile CVR = desktop × 0.60 at checkout+

activation:
  # 7-day activation rates by channel (pre-TikTok)
  organic: 0.40
  paid_search: 0.35
  social: 0.25
  referral: 0.45
  email: 0.30
  tiktok_ads: 0.12                  # post-launch

membership:
  trial_rate: 0.08                   # % of users who start a trial
  trial_to_paid_rate: 0.45
  monthly_churn_rate: 0.05
  annual_churn_rate: 0.02
  plan_split:
    monthly: 0.60
    annual: 0.40

support_tickets:
  base_rate_per_1000_users_per_day: 2.5
  category_distribution:
    payment_issue: 0.25
    delivery_issue: 0.30
    product_quality: 0.20
    account_issue: 0.15
    membership_issue: 0.05
    other: 0.05
  severity_distribution:
    low: 0.40
    medium: 0.35
    high: 0.20
    critical: 0.05
  resolution_hours:
    mean: 24
    std: 12
    min: 1
    max: 72

nps:
  free_nps_q1: 28
  free_nps_q2: 30
  plus_nps_q1: 52
  plus_nps_q2: 54
  responses_per_quarter: 2000
  q1_free_response_pct: 0.40
  q2_free_response_pct: 0.60
  q3_free_response_pct: 0.50
  q4_free_response_pct: 0.50
  comment_rate: 0.30

orders:
  items_per_order:
    mean: 2
    min: 1
    max: 4
  status_distribution:
    completed: 0.85
    cancelled: 0.10
    returned: 0.05
  shipping_non_plus: 5.99
  target_aov: 75.0

stories:
  ticket_spike:
    start: "2024-06-01"
    end: "2024-06-14"
    multiplier: 3.0
    category: "payment_issue"
    device: "ios"
    app_version: "2.3.0"

  activation_drop:
    target_pre_activation: 0.30
    target_post_activation: 0.24

  nps_paradox:
    # Controlled by nps section above

  power_user_fallacy:
    experiment_id: 1
    experiment_start: "2024-08-01"
    experiment_end: "2024-09-30"
    n_experiment_users: 10000
    observational_correlation: 3.0   # 3x purchase rate for SFL users
    true_causal_effect: 0.08         # 8% relative lift
    control_purchase_rate: 0.153
    treatment_purchase_rate: 0.165

  checkout_confound:
    experiment_id: 2
    redesign_date: "2024-11-20"
    promo_start: "2024-11-25"
    promo_end: "2024-12-01"
    mobile_cvr_baseline: 0.060
    mobile_cvr_redesign: 0.065
    desktop_cvr_baseline: 0.100
    promo_effect_pp: 0.030
    n_experiment_users: 10000

  mobile_gap:
    mobile_checkout_cvr: 0.060
    desktop_checkout_cvr: 0.100
    monthly_mobile_checkouts: 50000

app_versions:
  ios:
    - {version: "2.1.0", start: "2024-01-01", end: "2024-03-31"}
    - {version: "2.2.0", start: "2024-04-01", end: "2024-05-31"}
    - {version: "2.3.0", start: "2024-06-01", end: "2024-06-30"}
    - {version: "2.4.0", start: "2024-07-01", end: "2024-12-31"}
  android:
    - {version: "3.1.0", start: "2024-01-01", end: "2024-06-30"}
    - {version: "3.2.0", start: "2024-07-01", end: "2024-12-31"}

capstone:
  time_range: ["2023-01-01", "2023-12-31"]
  random_seed: 123
  landmines:
    duplicate_android_events_pct: 0.02
    missing_ios_events_window: ["2023-10-01", "2023-10-07"]
    delayed_timestamp_pct: 0.03
    delayed_timestamp_shift_hours: 7
    unstitched_sessions_pct: 0.05
    orphan_order_pct: 0.01
  structural:
    remove_sessions_table: true
    remove_nps_user_segment: true
    null_support_device_pct: 0.30
```

---

## 9. Quality Gates

Every gate must pass before the dataset is considered valid. Gates are run by `quality_gates.py`.

### 9.1 Row Count Gates

| Table | Min | Max |
|-------|-----|-----|
| users | 49,000 | 51,000 |
| products | 490 | 510 |
| calendar | 366 | 366 |
| promotions | 5 | 5 |
| experiments | 2 | 2 |
| events | 3,000,000 | 6,000,000 |
| sessions | 400,000 | 1,200,000 |
| orders | 25,000 | 60,000 |
| order_items | 50,000 | 150,000 |
| memberships | 8,000 | 20,000 |
| support_tickets | 15,000 | 40,000 |
| nps_responses | 7,000 | 9,000 |
| experiment_assignments | 18,000 | 22,000 |

### 9.2 Referential Integrity Gates (Practice Dataset)

| Gate | Rule |
|------|------|
| events → users | All events.user_id must exist in users.user_id |
| events → products | All non-null events.product_id must exist in products.product_id |
| orders → users | All orders.user_id must exist in users.user_id |
| order_items → orders | All order_items.order_id must exist in orders.order_id |
| order_items → products | All order_items.product_id must exist in products.product_id |
| support_tickets → users | All support_tickets.user_id must exist in users.user_id |
| nps_responses → users | All nps_responses.user_id must exist in users.user_id |
| experiment_assignments → users | All experiment_assignments.user_id must exist in users.user_id |
| experiment_assignments → experiments | All experiment_assignments.experiment_id must exist in experiments.experiment_id |
| orders → promotions | All non-null orders.promo_id must exist in promotions.promo_id |

### 9.3 Funnel Rate Gates

| Gate | Min | Max |
|------|-----|-----|
| product_view → add_to_cart | 20% | 30% |
| add_to_cart → checkout_started | 44% | 66% |
| checkout_started → payment_attempted | 64% | 96% |
| payment_attempted → purchase_complete | 72% | 95% |

### 9.4 Story Verification Gates

| Story | Gate | How to Verify |
|-------|------|---------------|
| 1: Ticket Spike | Jun 1-14 payment_issue tickets > 2.5x baseline | Compare daily avg in spike vs non-spike period |
| 1: Ticket Spike | 90%+ of spike is iOS | Device breakdown during spike |
| 2: Activation Drop | Post-June aggregate activation < pre-June by 4-8pp | Overall activation comparison |
| 2: Activation Drop | Within-channel rates stable (±2pp) | Channel-level activation pre vs post |
| 3: NPS Paradox | Q2 aggregate NPS < Q1 aggregate NPS | Aggregate comparison |
| 3: NPS Paradox | Q2 Free NPS > Q1 Free NPS | Segment comparison |
| 3: NPS Paradox | Q2 Plus NPS > Q1 Plus NPS | Segment comparison |
| 4: Power User | Observational SFL correlation > 2x | Compare purchase rates |
| 4: Power User | Experiment treatment effect < 15% relative | Experiment analysis |
| 5: Checkout Confound | Naive pre-post mobile lift > 20% | Pre vs during-promo comparison |
| 5: Checkout Confound | DiD estimate < 2pp | Desktop-controlled estimate |
| 6: Mobile Gap | Mobile CVR < Desktop CVR by ≥ 3pp | Device-level conversion comparison |

### 9.5 General Sanity Gates

| Gate | Rule |
|------|------|
| Time completeness | Every date in 2024 has ≥100 events (no gaps in practice data) |
| Retention monotonic | Month-N retention decreasing for N=1..12 |
| Holiday spike | Black Friday week orders > 1.5x normal week orders |
| No null PKs | No primary key column has NULL values |
| Date range | All dates within 2024-01-01 to 2024-12-31 |
| Signup before events | All events.event_timestamp ≥ user's signup_timestamp |

### 9.6 Capstone-Specific Gates

| Gate | Rule |
|------|------|
| Duplicates exist | ≥1.5% of Android events are duplicates |
| iOS gap exists | Zero iOS events for Oct 1-7 |
| Timestamp shifts | ≥2% of events have timestamps shifted |
| Orphan orders | ≥0.5% of orders have user_id not in users |
| No sessions table | sessions.csv does not exist in capstone/ |
| No user_segment | nps_responses.csv has no user_segment column |
| Device nulls | ≥25% of support_tickets have NULL device |

---

## 10. Course Query Pack

26 canonical queries that must produce expected results against the practice dataset.

### Week 3 Queries (10 queries)

**Q3.1 — Monthly Active Users (MAU)**
```sql
SELECT DATE_TRUNC('month', event_date) as month,
       COUNT(DISTINCT user_id) as mau
FROM events
GROUP BY 1 ORDER BY 1;
```
Expected: 12 rows, MAU growing from ~20K to ~40K over the year.

**Q3.2 — Revenue Metric Tree**
```sql
SELECT DATE_TRUNC('month', order_date) as month,
       COUNT(DISTINCT user_id) as active_buyers,
       COUNT(*) * 1.0 / COUNT(DISTINCT user_id) as orders_per_buyer,
       AVG(total_amount) as avg_order_value,
       SUM(total_amount) as total_revenue
FROM orders
WHERE status = 'completed'
GROUP BY 1 ORDER BY 1;
```
Expected: 12 rows, revenue with holiday spike in Nov-Dec.

**Q3.3 — Activation Rate by Cohort and Channel**
Expected: Shows Story 2 — TikTok cohorts have low activation.

**Q3.4 — Checkout Funnel by Device**
Expected: Shows Story 6 — Mobile has lower conversion at checkout steps.

**Q3.5 — Root Cause Decomposition of Activation Drop**
Expected: Story 2 — mix shift explains aggregate drop.

**Q3.6 — NPS by Segment (Simpson's Paradox)**
Expected: Story 3 — aggregate down, both segments up.

**Q3.7 — Support Ticket Trend**
Expected: Story 1 — spike in June, payment_issue category.

**Q3.8 — Retention Cohort Analysis**
Expected: Triangle table, monotonically decreasing, Plus members retain better.

**Q3.9 — Duplicate Detection**
Expected: Practice = 0 duplicates. Capstone = ~2% Android duplicates.

**Q3.10 — Guardrail: Support Ticket Rate During Feature Launch**
Expected: Must separate from iOS ticket spike (different timing).

### Week 4 Queries (8 queries)

**Q4.1 — Experiment Balance Check**
Expected: Treatment/control balanced on dimensions.

**Q4.2 — Experiment Primary Metric**
Expected: Story 4 — ~15.3% control, ~16.5% treatment.

**Q4.3 — Observational vs Experimental Comparison**
Expected: Story 4 — 3x observational vs 8% experimental.

**Q4.4 — Pre-Post: Checkout Redesign**
Expected: Story 5 — naive shows 58% lift.

**Q4.5 — Diff-in-Diff: Isolate Redesign Effect**
Expected: Story 5 — true effect ~0.5pp.

**Q4.6 — Experiment Guardrail Check**
Expected: AOV stable across variants.

**Q4.7 — Mixed Results: Conversion vs AOV**
Expected: Must calculate net revenue impact.

**Q4.8 — Power Calculation Inputs**
Expected: Real baseline numbers from data.

### Week 5 Queries (8 queries)

**Q5.1 — Mobile Checkout Gap Sizing**
Expected: Story 6 — $900K-$1.8M opportunity.

**Q5.2 — Sensitivity Analysis**
Expected: Table of scenarios.

**Q5.3 — Membership Conversion Funnel**
Expected: Trial rate ~8%, trial-to-paid ~45%.

**Q5.4 — Revenue by Category and Trend**
Expected: Seasonality in electronics.

**Q5.5 — Opportunity Stack Rank**
Expected: Prioritized list.

**Q5.6 — LTV by Acquisition Channel**
Expected: Referral highest, TikTok lowest.

**Q5.7 — Churn by Plan Type**
Expected: Monthly >> annual churn.

**Q5.8 — Checkout Abandonment Recovery**
Expected: Revenue recovery estimate.

---

## 11. Performance Considerations

### 11.1 Memory
The events table at 3-5M rows × ~10 columns will be ~2-4GB in memory as a DataFrame. Generation should:
- Process users in batches (e.g., 5,000 at a time) rather than all 50K at once
- Append to a list of DataFrames, then concat once at the end
- Use appropriate dtypes (int32 instead of int64 where possible, category for text columns)

### 11.2 Runtime
Expected generation time: 5-15 minutes for the full practice dataset on a modern laptop. The events table dominates. Progress bars (tqdm) should show which phase is running.

### 11.3 Determinism
- All random operations use `numpy.random.Generator` with seed from config
- Faker uses a seed from config
- Generation order must be deterministic
- Running generate.py twice with same config must produce identical output

---

## 12. Implementation Phases

### Phase 1: Foundation (config + dimensions + users)
**Scripts:** `config.yaml`, `generators/__init__.py`, `calendar_gen.py`, `products.py`, `promotions.py`, `experiments.py`, `users.py`
**Validates:** Dimension tables exist with correct row counts and distributions. Users have TikTok channel appearing Jun 1+.
**Estimated effort:** Small — these are simple generators.

### Phase 2: Events Engine (the big one)
**Scripts:** `sessions_and_events.py`
**Validates:** Events table is 3-5M rows, funnel conversion rates are within spec, app versions are correct, mobile penalty is applied.
**Estimated effort:** Large — this is the most complex generator. Must handle batching, funnel logic, session structure, and multiple stories.

### Phase 3: Derived Facts
**Scripts:** `orders.py`, `memberships.py`, `support_tickets.py`, `nps_responses.py`, `experiment_assignments.py`
**Validates:** All fact tables exist with correct row counts, FK integrity, distributions match spec.
**Estimated effort:** Medium — each is moderately complex.

### Phase 4: Story Injection
**Scripts:** `stories/ticket_spike.py`, `stories/nps_paradox.py`, `stories/power_user_fallacy.py`, `stories/checkout_confound.py`, `stories/activation_drop.py`
**Validates:** All 6 story verification gates pass.
**Estimated effort:** Medium — requires careful numerical tuning.

### Phase 5: Export + DuckDB
**Scripts:** `export.py`, `load_duckdb.py`
**Validates:** CSVs are readable, DuckDB loads successfully, queries return results.
**Estimated effort:** Small.

### Phase 6: Capstone
**Scripts:** `capstone/apply_landmines.py`, `capstone/capstone_stories.py`
**Validates:** All capstone-specific gates pass, landmines are detectable.
**Estimated effort:** Medium.

### Phase 7: Quality Gates + Final Validation
**Scripts:** `quality_gates.py`
**Validates:** All gates pass for both datasets. Run all 26 canonical queries.
**Estimated effort:** Medium — writing comprehensive validation logic.

---

## 13. Open Questions (None — All Resolved)

All design decisions have been made. Implementation can begin.

---

## 14. Glossary

| Term | Definition |
|------|-----------|
| **Activation** | User places first order within 7 days of signup |
| **MAU** | Monthly Active Users — users with ≥1 event in a calendar month |
| **NPS** | Net Promoter Score = %Promoters(9-10) - %Detractors(0-6), range -100 to +100 |
| **CVR** | Conversion Rate — typically purchases / checkout_started |
| **AOV** | Average Order Value — mean total_amount for completed orders |
| **DiD** | Difference-in-Differences — quasi-experimental method |
| **Plus** | NovaMart Plus membership (paid delivery/perks program) |
| **LTV** | Lifetime Value — total revenue from a user across all orders |
| **MDE** | Minimum Detectable Effect — smallest effect a test can detect at given power |
| **Simpson's Paradox** | Aggregate trend reverses when data is segmented |
