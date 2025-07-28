# Detailed Setup Guide

## Prerequisites

Before using this template, ensure you have:

- **Claude Code** installed and working
- **Node.js** (version 14 or higher) for documentation extraction
- **A project directory** where you want enhanced Claude Code behavior

## Installation Methods

### Method 1: Download ZIP (Recommended)

1. **Go to the GitHub repository**
2. **Click the green "Code" button**
3. **Select "Download ZIP"**
4. **Extract the files** to your project directory:
   ```bash
   cd your-project
   unzip claude-code-enhanced-template-main.zip
   mv claude-code-enhanced-template-main/* .
   mv claude-code-enhanced-template-main/.* . 2>/dev/null || true
   rm -rf claude-code-enhanced-template-main
   ```

### Method 2: Git Clone

```bash
# Clone the repository
git clone https://github.com/yourusername/claude-code-enhanced-template.git

# Copy files to your project
cd your-project
cp ../claude-code-enhanced-template/* .
cp ../claude-code-enhanced-template/.gitignore . 2>/dev/null || true
```

### Method 3: Direct Download with curl

```bash
cd your-project
curl -L https://github.com/yourusername/claude-code-enhanced-template/archive/main.zip -o template.zip
unzip template.zip
mv claude-code-enhanced-template-main/* .
rm -rf claude-code-enhanced-template-main template.zip
```

## First Run

1. **Navigate to your project directory**:
   ```bash
   cd your-project
   ```

2. **Start Claude Code**:
   ```bash
   claude
   ```

3. **Automatic setup will run**:
   ```
   🚀 Auto-Setup Detected
   
   This appears to be a fresh Claude Code project setup. I'm automatically:
   1. Extracting Claude Code documentation
   2. Setting up project references  
   3. Analyzing your project structure
   4. Customizing this CLAUDE.md for your specific project
   
   This will take a moment...
   ```

4. **Setup completion**:
   ```
   ✅ Setup Complete!
   
   Your Claude Code environment is now fully configured with:
   - Comprehensive documentation access
   - Project-specific customization
   - Quality gates and best practices
   - Auto-optimization workflows
   
   Ready for development! What would you like to work on?
   ```

## Manual Setup (If Auto-Setup Fails)

If the automatic setup doesn't work:

1. **Extract documentation manually**:
   ```bash
   node claude_docs_extractor.js
   ```

2. **Start Claude Code**:
   ```bash
   claude
   ```

3. **Trigger manual setup**:
   ```
   analyze this project and update CLAUDE.md
   ```

## Verifying Installation

After setup, you should see these files in your project:

### Generated Files (after first run)
- `claude-code-core-reference.md` - Comprehensive documentation
- `claude-code-quick-reference.md` - Essential commands
- `claude-code-mcp-reference.md` - MCP integration (if available)
- `README-claude-docs.md` - Documentation index

### Original Template Files
- `CLAUDE.md` - Main configuration (now customized for your project)
- `claude_docs_extractor.js` - Documentation extractor
- `All_claude_docs_metadata_enriched_output_markdown_YYYYMMDD.csv` - Documentation source

## Testing the Installation

1. **Test auto-optimization**:
   ```
   claude
   > The modal doesn't work right
   ```
   
   You should see Claude ask clarifying questions and propose a structured approach.

2. **Test quality gates**:
   ```
   claude
   > Write a test for the user component
   ```
   
   Claude should analyze existing test patterns before writing new tests.

3. **Test "OK, Go" protocol**:
   ```
   claude
   > OK, Go
   ```
   
   Claude should greet you and ask about your development goals.

## Troubleshooting

### Common Issues

#### "No CSV file found" Error
```bash
❌ No Claude documentation CSV file found
Expected filename pattern: All_claude_docs_metadata_enriched_output_markdown_YYYYMMDD.csv
```

**Solution**: Ensure the CSV file was copied correctly and matches the expected filename pattern.

#### Node.js Not Found
```bash
node: command not found
```

**Solution**: Install Node.js from [nodejs.org](https://nodejs.org/)

#### Documentation Extraction Fails
```bash
❌ Error extracting documentation: ...
```

**Solutions**:
1. Check that the CSV file isn't corrupted
2. Ensure you have write permissions in the directory
3. Try running with `node --trace-warnings claude_docs_extractor.js`

#### Claude Code Doesn't Detect CLAUDE.md
**Symptoms**: Claude Code behaves normally without template features

**Solutions**:
1. Ensure the file is named exactly `CLAUDE.md` (all caps)
2. Verify you're in the correct directory
3. Check that the file has proper permissions

### Getting Help

If you're still having issues:

1. **Check the GitHub issues** - Someone might have had the same problem
2. **Create a new issue** with:
   - Your operating system
   - Node.js version (`node --version`)
   - Claude Code version
   - Error messages (full text)
   - Steps you've already tried

## Updating

### When New Claude Code Features Are Released

1. **Download the latest CSV file** (we'll provide updates)
2. **Replace the old CSV** in your project directory
3. **Re-run the extractor**:
   ```bash
   node claude_docs_extractor.js
   ```
4. **The updated documentation** will be available immediately

### Updating the Template Itself

1. **Download the latest template** from GitHub
2. **Compare your customized CLAUDE.md** with the new template
3. **Merge improvements** while keeping your project-specific customizations
4. **Test the updated configuration**

## Advanced Configuration

### Custom Documentation Sources

If you have additional Claude Code documentation:

1. **Add your CSV files** to the project directory
2. **Modify the extractor** to include your categories
3. **Re-run extraction** to include your documentation

### Project-Specific Customization

The `CLAUDE.md` file can be customized for your specific needs:

- **Add project-specific commands**
- **Include team coding standards**
- **Reference project documentation**
- **Add custom quality gates**

See the file comments for customization guidance.

## Next Steps

After successful installation:

1. **Read through your customized CLAUDE.md** to understand the features
2. **Try the example workflows** to get familiar with the enhanced behavior
3. **Start with a simple development task** to test the system
4. **Provide feedback** by starring the repo or opening issues

Enjoy your enhanced Claude Code experience! 🚀