// Claude Code Documentation Extractor
// Run this script to extract key documentation from your CSV file
// and create organized reference files for Claude Code

import Papa from 'papaparse';
import fs from 'fs';

async function extractClaudeCodeDocs() {
  // Read the CSV file
  const csvContent = fs.readFileSync('All_claude_docs_metadata_enriched_output_markdown_20250721.csv', 'utf8');
  
  const parsedData = Papa.parse(csvContent, {
    header: true,
    dynamicTyping: true,
    skipEmptyLines: true
  });

  // Define priority categories for Claude Code
  const priorityCategories = {
    'installation': 'Installation & Setup',
    'configuration': 'Configuration',
    'getting-started': 'Getting Started',
    'mechanics': 'Claude Code Mechanics',
    'development': 'Development Workflows',
    'homepage': 'Overview & Concepts'
  };

  // Extract core Claude Code documentation
  const coreClaudeCodeDocs = parsedData.data.filter(item => 
    priorityCategories[item.category] && 
    item.markdown && 
    item.token_estimate > 100 // Filter for substantial content
  );

  // Group by category
  const groupedDocs = {};
  Object.keys(priorityCategories).forEach(category => {
    groupedDocs[category] = coreClaudeCodeDocs.filter(item => item.category === category);
  });

  // Create organized documentation files
  
  // 1. Core reference file
  let coreReference = `# Claude Code Core Documentation Reference\n\n`;
  coreReference += `Generated from ${parsedData.data.length} documentation entries\n\n`;
  
  Object.keys(priorityCategories).forEach(category => {
    if (groupedDocs[category].length > 0) {
      coreReference += `## ${priorityCategories[category]}\n\n`;
      groupedDocs[category].forEach(item => {
        coreReference += `### ${item.title}\n`;
        coreReference += `Source: ${item.url}\n`;
        coreReference += `Tokens: ${item.token_estimate}\n\n`;
        
        // Add markdown content but truncate if too long
        let content = item.markdown;
        if (content.length > 2000) {
          content = content.substring(0, 2000) + '...\n\n[Content truncated - see full source]';
        }
        coreReference += content + '\n\n---\n\n';
      });
    }
  });

  // 2. Quick reference commands file
  const quickReference = `# Claude Code Quick Reference

## Essential Commands
\`\`\`bash
# Interactive mode
claude

# One-shot commands
claude -p "your task description"

# File operations
claude -p "read src/file.js"
claude -p "edit src/file.js to add error handling"
claude -p "create a new component in src/components/"

# Project analysis
claude -p "analyze this codebase structure"
claude -p "find all TODO comments"
claude -p "explain the authentication flow"

# Development tasks
claude -p "add unit tests for the user service"
claude -p "refactor this component to use hooks"
claude -p "fix the TypeScript errors in this file"
\`\`\`

## "OK, Go" Activation
Type **"OK, Go"** to trigger Claude Code's discovery flow:
- Get oriented in your project
- See relevant capabilities
- Get suggestions for next steps
- Reset context if needed

## Best Practices from Documentation
${groupedDocs.mechanics ? groupedDocs.mechanics.map(item => 
  `- ${item.title}: Key insights for optimization`
).join('\n') : ''}

## Configuration Tips
- Always create a CLAUDE.md file in your project root
- Include project overview, coding standards, and important commands
- Reference this documentation for advanced techniques
- Use natural language to describe what you want to build
`;

  // 3. MCP (Model Context Protocol) reference if available
  const mcpDocs = parsedData.data.filter(item => 
    item.category === 'modelcontextprotocol' || 
    item.title?.toLowerCase().includes('mcp')
  );
  
  let mcpReference = '';
  if (mcpDocs.length > 0) {
    mcpReference = `# Model Context Protocol (MCP) Reference\n\n`;
    mcpDocs.forEach(item => {
      if (item.markdown) {
        mcpReference += `## ${item.title}\n`;
        mcpReference += `${item.markdown}\n\n---\n\n`;
      }
    });
  }

  // Write files
  fs.writeFileSync('claude-code-core-reference.md', coreReference);
  fs.writeFileSync('claude-code-quick-reference.md', quickReference);
  if (mcpReference) {
    fs.writeFileSync('claude-code-mcp-reference.md', mcpReference);
  }

  // Create a documentation index
  const indexFile = `# Claude Code Documentation Index

This directory contains extracted documentation from ClaudeLog and official sources.

## Files Created:
- **claude-code-core-reference.md**: Comprehensive documentation (${coreClaudeCodeDocs.length} entries)
- **claude-code-quick-reference.md**: Essential commands and workflows
${mcpReference ? '- **claude-code-mcp-reference.md**: Model Context Protocol integration\n' : ''}
- **CLAUDE.md**: Your project configuration (customize this!)

## How to Use:
1. Place CLAUDE.md in your project root
2. Reference the other files as needed when working with Claude Code
3. Type "OK, Go" in Claude Code to activate discovery mode
4. Use natural language to describe your development tasks

## Documentation Statistics:
- Total entries processed: ${parsedData.data.length}
- Core Claude Code entries: ${coreClaudeCodeDocs.length}
- Categories covered: ${Object.keys(priorityCategories).length}
- Token count: ${coreClaudeCodeDocs.reduce((sum, item) => sum + (item.token_estimate || 0), 0)}

Generated on: ${new Date().toISOString()}
`;

  fs.writeFileSync('README-claude-docs.md', indexFile);

  console.log('Claude Code documentation extracted successfully!');
  console.log(`Created ${coreClaudeCodeDocs.length} core documentation entries`);
  console.log('Files created:');
  console.log('- claude-code-core-reference.md');
  console.log('- claude-code-quick-reference.md');
  if (mcpReference) console.log('- claude-code-mcp-reference.md');
  console.log('- README-claude-docs.md');
  console.log('\nNext steps:');
  console.log('1. Customize the CLAUDE.md file for your project');
  console.log('2. Add these files to your project directory');
  console.log('3. Reference them in your CLAUDE.md file');
}

// Run the extractor
extractClaudeCodeDocs().catch(console.error);