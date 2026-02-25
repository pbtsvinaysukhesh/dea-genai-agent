# On-Device AI Memory Intelligence Agent

Automated AI research monitoring and analysis system focused on on-device AI workloads (mobile & laptops) with emphasis on memory, DRAM, storage, and bandwidth metrics.

## 🎯 Features

- **Automated Article Collection**: Fetches research from arXiv, RSS feeds, and vendor blogs
- **AI-Powered Analysis**: Uses Google Gemini to analyze relevance and extract insights
- **Memory-Focused Intelligence**: Specifically tracks DRAM, memory bandwidth, and optimization techniques
- **Historical Context**: Maintains research history and detects trends
- **Daily Email Reports**: Professional HTML reports sent automatically
- **Production-Ready**: Comprehensive error handling, retry logic, and logging

## 📋 Requirements

- Python 3.8+
- Google Gemini API key
- SMTP credentials (for email reports)

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone <your-repo-url>
cd on-device-ai-intelligence

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your credentials
# Required: GOOGLE_API_KEY
# Optional: SMTP_USER, SMTP_PASSWORD
```

Edit `config/config.yaml` to customize:
- Article sources (arXiv queries, RSS feeds)
- Relevance threshold
- Email recipients
- AI model selection

### 3. Test Configuration

```bash
python main.py test
```

This will:
- Validate configuration files
- Test API connectivity
- Send a test email (if SMTP configured)
- Fetch sample articles

### 4. Run Pipeline

```bash
python main.py
```

## 📁 Project Structure

```
on-device-ai-intelligence/
├── main.py                 # Main pipeline orchestrator
├── src/
│   ├── analyzer.py         # AI-powered article analysis
│   ├── collector.py        # Article collection from multiple sources
│   ├── formatter.py        # HTML report generation
│   ├── history.py          # Historical data and trend tracking
│   └── mailer.py           # Email delivery with retry logic
├── config/
│   └── config.yaml         # Configuration file
├── data/
│   └── history.json        # Historical article database
├── logs/                   # Application logs
├── reports/                # Generated HTML reports (if email fails)
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create from .env.example)
└── README.md              # This file
```

## ⚙️ Configuration Guide

### config/config.yaml

```yaml
system:
  relevance_threshold: 60      # Minimum score (0-100) for inclusion
  context_days: 7              # Days of history to use for context
  model_name: "gemini-2.0-flash-lite"  # AI model to use

sources:
  arxiv_queries:
    - "cat:cs.LG AND (all:edge OR all:mobile)"
    - "all:\"on-device AI\""
  
  rss_feeds:
    - "https://ai.googleblog.com/feeds/posts/default"
    - "https://machinelearning.apple.com/rss.xml"

email:
  recipients:
    - "team@example.com"
```

### Environment Variables (.env)

```bash
# Required
GOOGLE_API_KEY=your-api-key

# Optional (for email)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## 📊 Output Examples

### Email Report Structure

- **Daily Summary**: Stats on total articles, platforms, DRAM impact
- **Cross-Platform Highlights**: Research applicable to both mobile and laptop
- **Mobile Platform**: Mobile-specific findings
- **Laptop Platform**: Laptop-specific findings

### Each Article Includes:

- Relevance score
- Platform (Mobile/Laptop/Both)
- Model type (LLM, Vision, etc.)
- Memory insight with specific metrics
- DRAM impact (High/Medium/Low)
- Quantization method
- Engineering takeaway

## 🤖 AI Analysis

The system uses Google Gemini to:

1. **Score Relevance** (0-100): How relevant is this research to on-device memory?
2. **Extract Insights**: Identify key memory/DRAM findings
3. **Classify Platform**: Determine if it's for mobile, laptop, or both
4. **Detect Trends**: Connect new research to historical patterns
5. **Generate Takeaways**: Produce actionable engineering insights

### Scoring Rubric

- **90-100**: Direct on-device inference with specific memory metrics
- **70-89**: On-device AI with clear memory implications
- **50-69**: Edge/mobile AI without detailed memory analysis
- **30-49**: Tangentially related (training-focused but mentions inference)
- **0-29**: Irrelevant or cloud-only

## 📈 Statistics and Monitoring

The system tracks:

- Articles collected per run
- Success/failure rates for analysis
- Average relevance scores
- Historical trends (30-day view)
- Platform distribution
- DRAM impact distribution

View statistics:

```python
from src.history import HistoryManager

history = HistoryManager()
stats = history.get_statistics(days=30)
print(stats)
```

## 🔧 Advanced Usage

### Custom Model Selection

```yaml
# In config/config.yaml
system:
  model_name: "gemini-1.5-pro"  # More powerful, slower, more expensive
  # or
  model_name: "gemini-2.0-flash-lite"  # Specialized model
```

### Batch Processing with Progress

```python
from src.analyzer import AIProcessor
from src.collector import Collector

processor = AIProcessor(api_key="your-key")
collector = Collector()

articles = collector.fetch_all(config)

results = processor.process_batch(
    articles=articles,
    progress_callback=lambda curr, total, title: 
        print(f"[{curr}/{total}] {title[:50]}...")
)
```

### Export Historical Data

```python
from src.history import HistoryManager

history = HistoryManager()

# Export last 30 days to CSV
history.export_csv("output.csv", days=30)

# Search history
results = history.search_history("quantization", days=30)
```

## 🔄 Automation

### Daily Execution (Cron)

```bash
# Edit crontab
crontab -e

# Add line to run daily at 8 AM
0 8 * * * cd /path/to/project && /usr/bin/python3 main.py >> logs/cron.log 2>&1
```

### GitHub Actions (Example)

```yaml
name: Daily AI Report
on:
  schedule:
    - cron: '0 8 * * *'  # 8 AM daily

jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: python main.py
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
```

## 🐛 Troubleshooting

### Issue: "API key not found"

**Solution**: 
```bash
# Check .env file exists
cat .env

# Ensure GOOGLE_API_KEY is set
export GOOGLE_API_KEY="your-key"
```

### Issue: "Email sending failed"

**Solution**:
1. Check SMTP credentials in .env
2. For Gmail, use an App Password (not your regular password)
3. Enable "Less secure app access" or use OAuth2
4. Check logs: `tail -f logs/pipeline_*.log`

### Issue: "No articles found"

**Solution**:
1. Check internet connectivity
2. Verify arXiv queries are valid
3. Check RSS feed URLs are accessible
4. Review logs for specific errors

### Issue: "Low relevance scores"

**Solution**:
1. Adjust `relevance_threshold` in config.yaml (lower it)
2. Review arXiv queries - make them more specific
3. Add more relevant RSS feeds
4. Check if sources are actually publishing on-device research

## 📝 Development

### Run Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/ main.py
```

### Linting

```bash
flake8 src/ main.py
```

## 🔐 Security Notes

- **Never commit .env file** - it contains sensitive credentials
- Use App Passwords for Gmail (not your main password)
- Rotate API keys periodically
- Limit email recipient lists to authorized personnel
- Review logs for sensitive data before sharing

## 📊 Performance

### Typical Execution Times

- Article Collection: 30-60 seconds
- AI Analysis (50 articles): 2-5 minutes
- Report Generation: <5 seconds
- Email Sending: <5 seconds
- **Total**: 3-7 minutes for complete pipeline

### API Costs (Approximate)

Using Gemini 1.5 Flash:
- Cost per article: $0.0002-0.0005
- 50 articles/day: ~$0.01-0.025/day
- Monthly: ~$0.30-0.75/month

## 🛠️ Customization

### Adding New Sources

Edit `config/config.yaml`:

```yaml
sources:
  rss_feeds:
    - "https://your-custom-blog.com/feed"
```

### Custom Analysis Fields

Edit `src/analyzer.py` to add new extraction fields:

```python
# Add to prompt template
"new_field": "<description>",

# Add to validation
REQUIRED_FIELDS = [..., 'new_field']
```

### Custom Email Template

Edit `src/formatter.py`:

```python
def _build_article_card(self, item: Dict) -> str:
    # Customize HTML structure
    pass
```

## 📄 License

[Your License Here]

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📧 Support

For issues or questions:
- Check logs: `logs/pipeline_*.log`
- Review configuration: `python main.py test`
- Open an issue on GitHub

## 🙏 Acknowledgments

- Google Gemini API for AI analysis
- arXiv for open research access
- All the researchers advancing on-device AI

---

**Note**: This is an automated research monitoring tool. Always verify critical findings by reviewing the original papers.
