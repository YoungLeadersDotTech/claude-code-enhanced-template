# 📥 Input
- Topic: Easy Pay onboarding
- Labels: EasyPayExport
- Source: confluence, jira
- Output format: One PDF per Confluence space or Jira project
- Include images: ✅ Yes

# 🛠️ Action
Run the export script in the project directory:
python3 easy_pay_export.py

## From Confluence:
- For each Confluence space that contains matching pages:
  - Search for pages with the label `EasyPayExport`
  - Extract: title, author, last modified, body content
  - If the page contains **embedded images**, download and embed them inline where they appear in the content
  - Export as a PDF named:
    > `EasyPayExport_Confluence_{{SpaceName}}_{{Date}}.pdf`

## From Jira:
- For each Jira project with issues labeled `EasyPayExport`:
  - Extract: issue key, summary, status, assignee, description
  - If any issues have:
    - Embedded image links in the description → embed inline
    - Attachments of type PNG, JPG, or GIF → download and embed under a section labeled **“Attachments”**
  - Export as a PDF named:
    > `EasyPayExport_Jira_{{ProjectKey}}_{{Date}}.pdf`

# 🧾 Output
Each PDF must include:
- Title page with: label, space/project, and export date
- Table of contents
- One section per page/issue
- Inline images where available
- Horizontal dividers
- Markdown formatting

Use the export date in the format: `YYYY_MM_DD` (e.g., `2025_01_20`)

If an image cannot be embedded, show:
> ⚠️ Image could not be retrieved. View online: [image link]

If a space/project returns no results, skip that export.