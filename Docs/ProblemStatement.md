# App Review Insights Analyzer for Groww

## Problem Context
Groww is an investment platform that enables users to invest in stocks, mutual funds, and other financial instruments. User feedback from app reviews provides critical insights into user experiences, pain points, and feature requests. This project aims to systematically analyze Groww app reviews to extract actionable insights for product improvement.

## Objective
Turn recent App Store + Play Store reviews into a one-page weekly pulse containing:
Top themes
Real user quotes
Three action ideas
Finally send yourself a draft email containing this weekly note.

👥 Who This Helps
Product / Growth Teams → understand what to fix next
Support Teams → know what users are saying & acknowledging
Leadership → quick weekly health pulse

🛠️ What You Must Build
Import reviews from the last 8–12 weeks (rating, title, text, date)
Group reviews into 5 themes max (e.g., onboarding, KYC, payments, statements, withdrawals)
Generate a weekly one-page note:
Top 3 themes
3 user quotes
3 action ideas
Draft an email with the note (send to yourself/alias)
Do NOT include PII

⚠️ Key Constraints
Use public review exports only — no scraping behind logins
Max 5 themes
Keep notes scannable, ≤250 words
No usernames/emails/IDs in any artifacts

## Technical Implementation

### Integration Strategy
Instead of using direct APIs, this solution will leverage **MCP (Model Context Protocol) servers** for integration with Google Workspace services:
- **Google Docs MCP Server**: For creating and formatting the weekly one-page report document
- **Gmail MCP Server**: For drafting and sending the weekly pulse email

Using MCP servers provides a more secure, standardized approach to integrating with Google services, allowing the system to interact with Google Docs and Gmail through protocol-based communication rather than direct API calls.

### Workflow
1. Import Groww app reviews from the last 8–12 weeks (rating, title, text, date)
2. Group reviews into 5 themes max (e.g., onboarding, KYC, payments, statements, withdrawals)
3. Generate a weekly one-page note in Google Docs using MCP server:
   - Top 3 themes
   - 3 user quotes
   - 3 action ideas
4. Draft an email with the note using Gmail MCP server (send to yourself/alias)
5. Ensure no PII is included in any artifacts
