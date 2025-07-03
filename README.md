# BidSense.ca - Canadian Contractor Bid-Intel SaaS

**Free Alpha Launch** - AI-powered tender discovery and tracking for Canadian B2G contractors.

## 🎯 Mission

Transform how Canadian contractors discover and evaluate government tenders. From hours of manual scraping to minutes of AI-powered insights.

## 🚀 Tech Stack

- **Frontend**: Vite + React 18 + TypeScript + Tailwind CSS
- **Backend**: FastAPI (Python 3.12) + Poetry
- **Database**: Supabase (PostgreSQL 16 + pgvector)
- **Scraping**: Playwright + Apify proxy pool
- **AI**: OpenAI GPT-4o for summaries and insights
- **Email**: SendGrid + MJML templates
- **Deployment**: Railway (web + workers) + Cloudflare Pages
- **Analytics**: PostHog

## 📁 Project Structure

```
BidSenseCa/
├── frontend/          # React app (Vite + TypeScript)
├── backend/           # FastAPI server
├── scrapers/          # Playwright scraping scripts
├── infra/            # Infrastructure configs
└── docs/             # Documentation
```

## 🏃‍♂️ Quick Start

### Prerequisites
- Node.js 18+
- Python 3.12+
- Poetry
- Supabase account
- OpenAI API key

### Development Setup

1. **Clone and setup**
   ```bash
   git clone <repo-url>
   cd BidSenseCa
   ```

2. **Backend setup**
   ```bash
   cd backend
   poetry install
   poetry run uvicorn main:app --reload
   ```

3. **Frontend setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Scrapers setup**
   ```bash
   cd scrapers
   poetry install
   poetry run playwright install
   poetry run scrape-merx  # Test MERX scraper
   ```

5. **Environment variables**
   ```bash
   cp .env.example .env
   # Fill in your API keys and database URLs
   ```

## 🎯 Alpha Features

- ✅ Daily email digest of new tenders
- ✅ AI-generated tender summaries
- ✅ Historical award insights
- ✅ Bookmark and export functionality
- ✅ Province and NAICS filtering
- 🔄 AI Fit Score (Month 2)
- 🔄 Compliance Checklist (Month 2)

## 📊 Success Metrics

- Weekly Active Users: ≥70%
- NPS from free users: ≥+20
- Scraper success rate: ≥98%
- Digest open rate: ≥45%

## 🤝 Contributing

This is a solo founder project launching in 7 days. For alpha feedback, please use the in-app feedback form.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

**Status**: 🚧 Alpha Development (Day 2/7)
**Next Milestone**: Backend API endpoints, frontend integration
**Completed**: ✅ Infrastructure, ✅ MERX Scraper 