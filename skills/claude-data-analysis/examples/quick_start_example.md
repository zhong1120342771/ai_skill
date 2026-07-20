# Quick Start Example: User Behavior Analysis

This example demonstrates how to use the Claude Data Analysis Assistant to analyze user behavior data from start to finish.

## 📋 Prerequisites

Make sure you have:
- Claude Code installed and configured
- This project set up with the sample data
- Basic understanding of data analysis concepts

## 🚀 Step-by-Step Analysis

### Step 1: Data Preparation
Your data is already prepared in `data_storage/user_behavior_sample.csv`

```bash
# Check what data is available
ls -la data_storage/
```

### Step 2: Exploratory Analysis
Start with basic data exploration:

```bash
/analyze user_behavior_sample.csv exploratory
```

**Expected Output:**
The system will automatically:
- Load and inspect the data structure
- Generate summary statistics
- Identify data quality issues
- Provide initial insights

### Step 3: Create Visualizations
Generate comprehensive visualizations:

```bash
/visualize user_behavior_sample.csv all
```

**Expected Output:**
- Interactive dashboard with multiple chart types
- Distribution analysis
- Correlation heatmap
- Time series trends
- User behavior patterns

### Step 4: Generate Analysis Code
Create reusable analysis code:

```bash
/generate python user-segmentation
```

**Expected Output:**
- Python scripts for user segmentation analysis
- Utility functions for data preprocessing
- Visualization code
- Documentation and examples

### Step 5: Generate Comprehensive Report
Create a complete analysis report:

```bash
/report user_behavior_sample.csv complete markdown
```

**Expected Output:**
- Executive summary
- Detailed statistical findings
- Key insights and recommendations
- Visualization descriptions
- Technical appendix

## 📊 Understanding the Data

### Sample Data Structure
The `user_behavior_sample.csv` contains:

| Column | Description | Type |
|--------|-------------|------|
| user_id | Unique user identifier | String |
| session_id | Session identifier | String |
| timestamp | Action timestamp | DateTime |
| action | User action type | String |
| page_url | Page visited | String |
| device_type | Device used | String |
| location | Geographic location | String |
| revenue | Revenue generated | Float |

### Action Types
- `page_view`: User viewed a page
- `click`: User clicked on something
- `purchase`: User made a purchase

### Device Types
- `desktop`: Desktop computer
- `mobile`: Mobile device
- `tablet`: Tablet device

## 🎯 Expected Analysis Results

### Key Metrics
- **Total Users**: Number of unique users
- **Session Count**: Total number of sessions
- **Conversion Rate**: Percentage of sessions ending in purchase
- **Average Revenue**: Mean revenue per session
- **Device Distribution**: Usage by device type

### Insights to Discover
1. **User Behavior Patterns**: How users navigate through the site
2. **Device Preferences**: Which devices are most popular
3. **Conversion Patterns**: What leads to purchases
4. **Geographic Trends**: Location-based behavior differences
5. **Time-based Patterns**: When users are most active

## 🔍 Advanced Analysis

### Custom Analysis
For more specific analysis, try:

```bash
# Statistical analysis
/analyze user_behavior_sample.csv statistical

# Predictive analysis
/analyze user_behavior_sample.csv predictive

# Quality check
/quality user_behavior_sample.csv clean

# Generate hypotheses
/hypothesis user_behavior_sample.csv user-engagement
```

### Custom Code Generation
Generate code for specific tasks:

```bash
# Data cleaning code
/generate python data-cleaning

# Statistical analysis code
/generate r statistical

# SQL queries
/generate sql reporting

# Machine learning
/generate python machine-learning
```

## 📈 Example Workflow Commands

### Complete Analysis Workflow
```bash
# 1. Exploratory analysis
/analyze user_behavior_sample.csv exploratory

# 2. Create visualizations
/visualize user_behavior_sample.csv trends

# 3. Generate code
/generate python user-segmentation

# 4. Create report
/report user_behavior_sample.csv complete html

# 5. Quality validation
/quality user_behavior_sample.csv validate
```

### Quick Analysis
```bash
# Quick overview
/analyze user_behavior_sample.csv exploratory

# Quick visualizations
/visualize user_behavior_sample.csv distribution

# Quick report
/report user_behavior_sample.csv summary markdown
```

## 🎨 Expected Outputs

### Files Generated
```
visualizations/
├── dashboard_user_behavior_sample.html  # Interactive dashboard
├── summary_user_behavior_sample.png      # Summary charts
└── detailed_user_behavior_sample.pdf     # Detailed analysis

generated_code/
├── python_user_segmentation.py          # Analysis code
├── user_segmentation_utils.py           # Utility functions
└── requirements_python.txt               # Dependencies

analysis_reports/
├── complete_analysis_user_behavior_sample.md  # Full report
└── summary_user_behavior_sample.md           # Summary report
```

### Key Findings
The analysis should reveal:
- **User Engagement**: How users interact with the platform
- **Conversion Patterns**: What drives purchases
- **Device Insights**: Which devices perform best
- **Geographic Trends**: Location-based differences
- **Revenue Patterns**: Revenue generation insights

## 🛠️ Customization

### Modify Analysis Parameters
You can customize the analysis by:
- Specifying different analysis types
- Requesting specific chart types
- Setting custom parameters for code generation
- Choosing different output formats

### Extend Functionality
To extend the analysis:
1. Add your own data files to `data_storage/`
2. Modify agent configurations in `.claude/agents/`
3. Create custom commands in `.claude/commands`
4. Add automation hooks in `.claude/settings.json`

## 🔍 Troubleshooting

### Common Issues
1. **Data Loading Issues**: Ensure data files are in CSV format
2. **Command Not Found**: Make sure you're in the project directory
3. **Permission Issues**: Check file permissions for data files
4. **Memory Issues**: Large datasets may require processing in chunks

### Getting Help
- Use `/help` for available commands
- Check the main README.md for project overview
- Review agent configurations for available tools

---

**Next Steps**: After completing this example, try with your own data or explore more advanced analysis types!