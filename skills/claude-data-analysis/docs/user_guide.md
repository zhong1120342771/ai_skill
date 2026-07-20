# User Guide

## Getting Started

### First-Time Setup

1. **Clone the project** (if you haven't already):
   ```bash
   git clone <repository-url>
   cd claude-data-analysis
   ```

2. **Verify Claude Code is running**:
   ```bash
   /help
   ```

3. **Check available agents**:
   ```bash
   /agents
   ```

### Basic Concepts

#### Sub-Agents
Specialized AI assistants that handle specific tasks:
- **data-explorer**: Statistical analysis and insights
- **visualization-specialist**: Charts and visualizations
- **code-generator**: Code generation
- **report-writer**: Report creation
- **quality-assurance**: Data validation
- **hypothesis-generator**: Research hypotheses

#### Slash Commands
Commands you type to perform actions:
- `/analyze [dataset] [type]`: Analyze data
- `/visualize [dataset] [type]`: Create visualizations
- `/generate [language] [type]`: Generate code
- `/report [dataset] [format]`: Create reports
- `/quality [dataset] [action]`: Quality checks
- `/hypothesis [dataset] [domain]`: Generate hypotheses

#### Hooks
Automated processes that run on events:
- Data validation when files are added
- Context loading when you start analysis
- Quality checks during analysis

## Common Workflows

### 1. Exploratory Data Analysis

```bash
# Start with basic exploration
/analyze your_data.csv exploratory

# Create visualizations
/visualize your_data.csv distribution

# Generate code for deeper analysis
/generate python statistical-analysis
```

### 2. Complete Analysis Project

```bash
# Full analysis workflow
/analyze your_data.csv complete
/visualize your_data.csv all
/report your_data.pdf
/generate python machine-learning
/quality your_data.csv validate
```

### 3. Business Intelligence

```bash
# Sales analysis example
/analyze sales_data.csv statistical
/visualize sales_data.csv trends
/generate sql revenue-report
/report sales_data.csv executive pdf
```

## Data Preparation

### Supported Formats
- **CSV**: Comma-separated values
- **JSON**: JavaScript Object Notation
- **Excel**: .xlsx files
- **Parquet**: Columnar storage format
- **SQL**: Database queries

### Data Structure Guidelines
- Use meaningful column names
- Include data type information
- Handle missing values consistently
- Document data sources and transformations

### Example Data Format

```csv
user_id,timestamp,action,value,revenue
user_001,2024-01-15 09:30:00,click,product_123,0.00
user_001,2024-01-15 09:35:00,purchase,product_123,29.99
```

## Command Reference

### /analyze Command

**Syntax**: `/analyze [dataset] [analysis_type]`

**Analysis Types**:
- `exploratory`: Basic data exploration and summary
- `statistical`: Advanced statistical analysis
- `predictive`: Predictive modeling preparation
- `complete`: Comprehensive analysis including all types

**Examples**:
```bash
/analyze user_data.csv exploratory
/analyze sales_data.csv statistical
/analyze customer_data.csv predictive
/analyze financial_data.csv complete
```

### /visualize Command

**Syntax**: `/visualize [dataset] [chart_type]`

**Chart Types**:
- `all`: Comprehensive dashboard
- `trends`: Time series and trend analysis
- `distribution`: Histograms, box plots, density plots
- `correlation`: Correlation matrices and heatmaps
- `comparison`: Bar charts, grouped comparisons
- `custom`: User-specified custom visualizations

**Examples**:
```bash
/visualize user_data.csv all
/visualize sales_data.csv trends
/visualize customer_data.csv distribution
/visualize financial_data.csv custom
```

### /generate Command

**Syntax**: `/generate [language] [analysis_type]`

**Languages**:
- `python`: Python data analysis code
- `r`: R statistical analysis
- `sql`: Database queries
- `javascript`: Web-based visualizations

**Analysis Types**:
- `data-cleaning`: Data preprocessing and cleaning
- `statistical`: Statistical analysis code
- `visualization`: Chart and graph generation
- `machine-learning`: ML model training
- `custom`: Custom analysis requirements

**Examples**:
```bash
/generate python data-cleaning
/generate r statistical
/generate sql reporting
/generate javascript visualization
```

### /report Command

**Syntax**: `/report [dataset] [format]`

**Formats**:
- `summary`: Brief overview and key findings
- `complete`: Comprehensive detailed report
- `executive`: Business-focused summary
- `technical`: Technical documentation

**Output Formats**:
- `markdown`: Markdown format
- `html`: Web page format
- `pdf`: PDF document
- `json`: Structured data format

**Examples**:
```bash
/report user_data.csv complete markdown
/report sales_data.csv executive pdf
/report customer_data.csv technical json
```

### /quality Command

**Syntax**: `/quality [dataset] [action]`

**Actions**:
- `check`: Basic data quality assessment
- `clean`: Clean data issues
- `validate`: Comprehensive validation
- `monitor`: Set up ongoing monitoring

**Examples**:
```bash
/quality user_data.csv check
/quality sales_data.csv clean
/quality customer_data.csv validate
/quality financial_data.csv monitor
```

### /hypothesis Command

**Syntax**: `/hypothesis [dataset] [domain]`

**Domains**:
- `user-behavior`: User behavior patterns
- `business-impact`: Business performance
- `technical`: Technical performance
- `custom`: Custom domain analysis

**Examples**:
```bash
/hypothesis user_data.csv user-behavior
/hypothesis sales_data.csv business-impact
/hypothesis system_data.csv technical
```

## Working with Results

### Output Files

Generated files are organized in directories:

```
claude-data-analysis/
├── analysis_reports/    # Generated reports
├── visualizations/      # Charts and graphs
├── generated_code/     # Analysis code
└── data_storage/       # Your data files
```

### Understanding Reports

Reports typically include:
- **Executive Summary**: Key findings in business terms
- **Methodology**: Analysis approach and assumptions
- **Statistical Findings**: Detailed statistical results
- **Visualizations**: Charts and graphs with explanations
- **Recommendations**: Actionable insights
- **Limitations**: Data and method constraints
- **Appendix**: Technical details and code

### Interpreting Visualizations

Common chart types and what they show:
- **Line Charts**: Trends over time
- **Bar Charts**: Comparisons between categories
- **Scatter Plots**: Relationships between variables
- **Heatmaps**: Correlation and intensity patterns
- **Box Plots**: Distribution and outliers
- **Histograms**: Frequency distributions

## Troubleshooting

### Common Issues

#### Data Loading Problems
**Issue**: "Cannot read data file"
**Solution**:
- Check file is in `data_storage/` directory
- Verify file format is supported
- Ensure file has read permissions
- Check for proper encoding (UTF-8)

#### Command Not Found
**Issue**: "Command not recognized"
**Solution**:
- Verify you're in the project directory
- Check command spelling
- Use `/help` to see available commands
- Ensure Claude Code is properly configured

#### Analysis Takes Too Long
**Issue**: Analysis is slow or hangs
**Solution**:
- Check dataset size (large files take longer)
- Monitor system resources
- Consider data sampling for initial analysis
- Break analysis into smaller chunks

#### Poor Quality Results
**Issue**: Analysis results don't make sense
**Solution**:
- Check data quality and format
- Verify analysis parameters
- Try different analysis types
- Review data preparation steps

### Getting Help

#### Built-in Help
```bash
/help              # Show all available commands
/help [command]    # Get help for specific command
/agents            # List available agents
/status            # Check system status
```

#### Documentation
- Main README.md: Project overview
- examples/ directory: Usage examples
- docs/ directory: Detailed documentation
- CLAUDE.md: Claude Code specific guidance

#### Community Support
- Check project issues and discussions
- Review existing troubleshooting guides
- Submit bug reports with detailed information
- Ask questions with reproducible examples

## Best Practices

### Data Preparation
- **Clean Data First**: Remove duplicates, handle missing values
- **Document Everything**: Record data sources and transformations
- **Use Consistent Formats**: Standardize date formats, units
- **Validate Data**: Check for outliers and errors

### Analysis Approach
- **Start Simple**: Begin with exploratory analysis
- **Iterate**: Refine analysis based on findings
- **Validate**: Cross-check important results
- **Document**: Keep thorough analysis notes

### Working with Agents
- **Be Specific**: Provide clear requirements
- **Use Context**: Include relevant background information
- **Review Results**: Always review and validate outputs
- **Provide Feedback**: Help improve agent performance

### Code Generation
- **Test Generated Code**: Always test before production use
- **Customize as Needed**: Modify generated code for your needs
- **Understand the Code**: Don't use code you don't understand
- **Version Control**: Keep track of code changes

## Advanced Features

### Custom Agents
Create your own specialized agents by:
1. Creating new agent files in `.claude/agents/`
2. Defining specific expertise and capabilities
3. Configuring appropriate tool access
4. Testing with relevant use cases

### Custom Commands
Add custom commands by:
1. Creating command files in `.claude/commands/`
2. Defining command parameters and behavior
3. Setting appropriate tool permissions
4. Adding comprehensive documentation

### Automation Hooks
Set up automated workflows by:
1. Configuring hooks in `.claude/settings.json`
2. Writing automation scripts
3. Testing with different scenarios
4. Monitoring performance and results

## Integration

### With Existing Tools
- **Jupyter Notebooks**: Export code for notebook use
- **Business Intelligence Tools**: Generate SQL for BI platforms
- **Web Applications**: Create interactive dashboards
- **Data Pipelines**: Integrate with ETL processes

### With Team Workflows
- **Version Control**: Track analysis and code changes
- **Collaboration**: Share agents and commands
- **Documentation**: Maintain consistent documentation
- **Quality Assurance**: Implement team-wide standards

---

This guide provides a comprehensive overview of using the Claude Data Analysis Assistant. Start with the basic workflows and gradually explore more advanced features as you become comfortable with the platform.