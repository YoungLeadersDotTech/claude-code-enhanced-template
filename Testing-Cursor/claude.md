# CLAUDE.md - Enhanced Claude Code Project Configuration

## Project Overview

**Project Name**: [Your Project Name]
**Main Technologies**: [e.g., React, TypeScript, Node.js, Python, etc.]
**Purpose**: [Brief description of what this project does]

## Auto-Update Instructions for Claude

### Initial Setup Detection & Documentation Extraction
**When you see this template in a new project directory, follow this exact sequence:**

1. **Check for documentation files** - Look for `claude_docs_extractor.js` and `All_claude_docs_metadata_enriched_output_markdown_*.csv`

2. **Extract documentation first** (if files present):
   ```bash
   node claude_docs_extractor.js
   ```
   This creates the reference documentation files for this project.

3. **Update CLAUDE.md documentation references**:
   ```
   🔧 **Documentation Extraction Complete**
   
   I've processed the Claude Code documentation and created reference files:
   - claude-code-core-reference.md: Comprehensive documentation
   - claude-code-quick-reference.md: Essential commands
   - claude-code-mcp-reference.md: Model Context Protocol integration (if available)
   
   **Next: I'll update this CLAUDE.md to reference these files and then analyze your project.**
   ```

4. **Add documentation references** to the CLAUDE.md file:
   ```markdown
   ## Documentation References
   
   ### Quick Access
   - Core commands: See `claude-code-quick-reference.md`
   - Advanced techniques: See `claude-code-core-reference.md`
   - MCP integration: See `claude-code-mcp-reference.md` (if available)
   
   ### Context Commands
   ```bash
   # Load documentation context
   claude -p "reference the claude-code-core-reference.md file for advanced techniques"
   
   # Get specific guidance
   claude -p "show me the best practices from the mechanics documentation"
   
   # Troubleshoot issues
   claude -p "check the FAQ section in our documentation for this error"
   ```
   ```

5. **ONLY AFTER documentation is set up** - proceed with project template analysis

### Template Detection & Project Analysis
**After documentation setup, when you see placeholder text in brackets like `[Your Project Name]`:**

**Required Actions:**
1. **Analyze the project structure** to understand:
   - Primary technologies and frameworks used
   - Project purpose based on code, README, package.json, etc.
   - Main directories and file organization patterns

2. **Suggest specific updates** in this format:
   ```
   🔧 **CLAUDE.md Template Update Suggested**
   
   Documentation is now set up. Based on your project analysis:
   
   **Proposed Updates:**
   - Project Name: [detected name from package.json/folder/README]
   - Main Technologies: [detected stack - React, Node.js, TypeScript, etc.]
   - Purpose: [inferred from code structure and README]
   - File Structure: [detected patterns]
   
   **Should I update the CLAUDE.md file with these details?**
   ```

3. **Update the CLAUDE.md file** if confirmed, replacing placeholders with actual project information

### Documentation Updates & CSV Replacement
**For updating Claude Code documentation with new releases:**

1. **Detect new CSV files**: Look for newer `All_claude_docs_metadata_enriched_output_markdown_*.csv` files

2. **Backup and replace**:
   ```bash
   # Backup old documentation
   mkdir -p docs-backup/$(date +%Y%m%d)
   mv claude-code-*.md docs-backup/$(date +%Y%m%d)/
   
   # Extract new documentation
   node claude_docs_extractor.js
   ```

3. **Update references**: Check if new documentation categories or important changes need to be reflected in CLAUDE.md

### Staleness Detection
**Periodically check** (every 10-15 interactions) if project info needs updates:
- Has the tech stack changed significantly?
- Has the project purpose evolved based on recent code changes?
- Are new frameworks or major dependencies being used?
- Has the file structure changed substantially?
- Are there newer Claude Code documentation files available?

**If updates needed:**
```
💡 **CLAUDE.md Refresh Suggested**

Your project seems to have evolved:
- [Specific changes detected]
- [New technologies found]
- [Updated purpose based on recent work]
- [New documentation available: date of newer CSV file]

Should I refresh the CLAUDE.md with current project state?
```

### Required Setup Files
**This template expects these files in the project directory:**
- `claude_docs_extractor.js` - Documentation extraction script
- `All_claude_docs_metadata_enriched_output_markdown_YYYYMMDD.csv` - Claude Code documentation
- `CLAUDE.md` - This configuration file (template → customized)

### Project Analysis Commands
Use these to gather project information:
- Check `package.json`, `requirements.txt`, `Cargo.toml`, etc. for dependencies
- Examine `README.md` for project description
- Analyze directory structure for framework patterns
- Look for configuration files (`.babelrc`, `tsconfig.json`, etc.)
- Review recent commit messages or file changes for project evolution
- Scan for newer documentation CSV files to keep Claude Code knowledge current

## Core Claude Code Capabilities
- **Terminal Integration**: Operates directly in your terminal, understanding project context
- **Multi-file Operations**: Make powerful edits across multiple files with codebase understanding  
- **Git Workflow Management**: Read issues, write code, run tests, and submit PRs from the terminal
- **Extended Thinking**: Handle complex architectural decisions and multi-step implementations
- **Natural Language Commands**: Use plain English instead of complex CLI syntax

### Compatibility & Integration Support
This configuration works with:
- Claude Code CLI (terminal usage)
- Claude Code VS Code Extension
- Claude Code with Amazon Bedrock integration
- Claude Code with Google Vertex AI integration
- Claude Code in development containers
- Claude Code with GitHub Actions
- Claude Code with MCP (Model Context Protocol)

### Common Commands
```bash
# Interactive mode
claude

# One-shot mode for quick tasks
claude -p "Show me the files in this directory"

# File operations
read src/components/Button.js
edit src/components/Button.js
write src/components/NewComponent.js

# Code analysis
analyze this codebase
find all React components
explain how authentication works

# Development tasks
add a dark mode toggle to the app
fix the memory leak in the data fetcher
refactor the user service to use TypeScript
write unit tests for the Button component
```

### Smart Response Formatting
- **Executable Commands**: Show in code blocks with bash syntax highlighting
- **Natural Language Explanations**: Use conversational text for easy reading
- **Override Options**: 
  - Say "Show me the raw command" → get exact terminal syntax
  - Say "Explain this more simply" → get plain language without code blocks

### Role & Audience Context
Claude Code is designed for developers working on:
- Rapid prototyping and feature development
- Code refactoring and modernization
- Debugging and problem-solving
- Test writing and documentation
- Multi-file architectural changes
- Automated development workflows
- Enterprise development with Bedrock/Vertex AI

Key principle: Claude Code operates directly in the development environment, unlike copy-paste AI coding tools.

## Claude Code Philosophy & Approach

### Paradigm Shift
Claude Code represents a fundamentally different approach to AI-assisted development:
- **Describe what you want** in natural language
- **Claude Code handles implementation** directly in your development environment
- **Monitor and steer progress** in real-time rather than copy-pasting snippets
- **Review completed work** instead of manually integrating AI suggestions

### Goal & Objective
Empower developers to move quickly from idea to implementation. Claude Code understands that developers need:
- **Quick orientation** when jumping into projects
- **Natural conversation** about complex technical problems
- **Direct action** in their actual development environment
- **Flexible interaction** from simple commands to complex architectural decisions

This CLAUDE.md serves as your project's context and instruction set, enabling Claude Code to work effectively within your specific development environment and coding standards.

## Prompt Optimization Instructions for Claude

### IMPORTANT: Auto-Detect and Optimize Unstructured Input

When user input contains any of these patterns, **AUTOMATICALLY** offer to optimize before proceeding:

#### Trigger Indicators for Optimization:
- **Vague language**: "I want to", "maybe we should", "I think I need"
- **Multiple disconnected ideas**: Stream of consciousness with 3+ different topics
- **Missing context**: No mention of specific files, components, or requirements
- **Unclear scope**: "Fix this", "make it better", "update the thing"
- **Complex nested requests**: Multiple sub-tasks without clear prioritization
- **Technical jargon without specifics**: "optimize performance", "improve UX", "add functionality"

#### Required Response Format:
```
🔧 **Let me help optimize this request**

What I understood:
[Clear summary of their main goals]

I need to clarify:
1. [Specific question about files/components]
2. [Question about scope or requirements]  
3. [Question about success criteria]
4. [Technical constraint question if relevant]

Suggested approach:
[Structured plan with specific steps]

Should I proceed with this approach, or would you like to adjust anything?
```

### Optimization Best Practices

#### Always Structure Requests With:
1. **Context First**: Specific files, components, or project areas
2. **Clear Action**: Actionable verb with specific outcome
3. **Success Criteria**: What "done" looks like
4. **Constraints**: Technical requirements, patterns to follow

#### Example Transformations:

**Before (Unstructured):**
> "The modal is being weird and sometimes doesn't close and I think it's the state management"

**After (Optimized):**
> "I'll investigate the modal closing issue. First, let me examine the modal component files to understand the current state management. I'll look for useEffect dependencies and state update patterns that might prevent proper closing. Would you like me to start with a specific modal component file?"

**Before (Vague):**
> "I want to add authentication to my app with login and JWT tokens"

**After (Optimized):**  
> "I'll create a complete authentication system. Let me clarify: Do you have existing user management files? What database are you using? Should I create new files or modify existing ones? I'll plan the auth flow including login/signup endpoints, JWT middleware, and secure token handling."

### Required Clarification Questions

Always ask about:
- **File Context**: "Which specific files should I examine/modify?"
- **Current State**: "What's working now vs. what you want to change?"
- **Scope**: "Is this a single component change or system-wide update?"
- **Patterns**: "Should I follow existing code patterns in the project?"
- **Success**: "How will we know this is complete and working?"

### Implementation Approach

1. **Detect** unstructured input automatically
2. **Summarize** what you understood from their request
3. **Ask 2-4 specific clarifying questions**
4. **Propose a structured approach** with clear steps
5. **Confirm before proceeding** with the work

## Project Overview

**Project Name**: [Your Project Name]
**Main Technologies**: [e.g., React, TypeScript, Node.js, Python, etc.]
**Purpose**: [Brief description of what this project does]

## Documentation Context

This project has access to comprehensive Claude Code documentation including:
- Installation and configuration guidance (969 tokens)
- Development mechanics and best practices (8 documented techniques)
- Getting started workflows
- Model Context Protocol (MCP) integration (10 components)
- Advanced troubleshooting and optimization techniques

### Key Documentation Sources
- ClaudeLog.com mechanics and best practices
- Official Claude Code documentation
- Community-tested techniques from r/ClaudeAI
- Enterprise integration patterns for Bedrock/Vertex AI

## Development Guidelines

### Coding Standards
- Follow existing code conventions in the project
- Use descriptive variable and function names
- Include inline comments for complex logic
- Maintain consistent file structure

### File Structure Preferences
```
[Auto-detected structure will be inserted here]
src/
├── components/          # Reusable UI components
├── pages/              # Page-level components
├── utils/              # Helper functions
├── services/           # API and business logic
├── types/              # TypeScript type definitions
└── tests/              # Test files
```

**Note**: The above is a template. During first analysis, replace with actual project structure.

## Testing & Code Quality Requirements

### CRITICAL: All Code Must Work
**Before completing any task, verify:**
- [ ] Code compiles without errors
- [ ] All tests pass (existing and new)
- [ ] Linting passes with no blocking issues
- [ ] TypeScript types are respected and accurate
- [ ] No access to non-existent object properties/methods

### Testing Strategy & Requirements
- **Write tests that actually work** - Mock objects must have correct method signatures
- **Respect existing test patterns** - Follow established mocking and testing conventions
- **Type-safe mocking** - Ensure mocked methods match actual implementation types
- **Test real scenarios** - Don't test non-existent functionality or properties
- **Verify imports and dependencies** - Ensure all test imports are valid and available

### Code Quality Checklist
```bash
# Always run these before considering task complete:
npm run type-check     # TypeScript validation
npm run lint          # Code style and basic errors  
npm run test          # Full test suite
npm run build         # Compilation verification
```

**If any of these fail, the task is not complete.**

## Claude Code Specific Instructions

### Natural Language Usage
Encourage conversational description of development needs:
- "I need a user authentication system with JWT tokens"
- "Fix the bug where the modal doesn't close properly"
- "Refactor the data fetching to use React Query"
- "Add error handling to all API calls"

But ALWAYS optimize vague requests into specific, actionable plans.

### Multi-file Operations
Excel at understanding relationships between files:
- "Update the user interface and the corresponding API endpoint"
- "Refactor the authentication flow across all components"
- "Add TypeScript types to the entire user management system"

## Context Building & Planning Strategy

### Required Planning-First Approach
**For any significant task:**
1. **Analyze existing code first** - Understanding current patterns, types, and architecture
2. **Create a detailed plan** - Break down into specific, verifiable steps
3. **Identify dependencies and constraints** - What files/types/patterns must be maintained
4. **Get explicit confirmation** - "Here's my plan: [detailed steps]. Should I proceed?"
5. **Execute iteratively** - Complete steps with validation at each stage

### Context Building Requirements
- **Never one-shot complex tasks** - Build understanding incrementally
- **Ask for specific file examination** - "Should I analyze [specific files] first?"
- **Understand project patterns** - Learn existing conventions before adding new code
- **Verify type definitions** - Check actual TypeScript interfaces before using them
- **Confirm dependency usage** - Understand how existing dependencies are used

### Dependency Management Rules
- **Analyze before removing** - Use dependency analysis tools when available
- **Understand usage patterns** - Check how dependencies are actually used across codebase
- **Verify removal safety** - Confirm dependencies aren't used in ways that aren't immediately obvious
- **Ask for confirmation** - "I found these dependencies that appear unused: [list]. Should I remove them?"

### Interruption & Iteration Protocol
- **Expect course corrections** - Be ready to adjust approach based on new information
- **Ask for clarification** - When uncertain, ask specific questions rather than making assumptions
- **Validate understanding** - "My understanding is [specific details]. Is this correct?"
- **Iterate on feedback** - Use corrections to improve subsequent attempts

## Session Management Commands

### End-of-Session Documentation
```bash
# Capture learnings and update documentation
claude -p "What did we learn in this session? Summarize key insights, any patterns discovered, common errors encountered, and suggest updates to CLAUDE.md based on this work."

# Update CLAUDE.md with session learnings
claude -p "Based on our work today, update the CLAUDE.md file to improve future sessions. Include any new patterns, gotchas, or process improvements we discovered."
```

### Context Building Commands  
```bash
# Before starting complex work
claude -p "Analyze the [component/service/feature] to understand existing patterns, types, and architecture before we make changes."

# For dependency work
claude -p "Analyze this project's dependency usage patterns and identify any truly unused dependencies with evidence of their usage or non-usage."

# For testing work  
claude -p "Examine existing test patterns and mocking strategies in this project before writing new tests."
```

### Validation Commands
```bash
# Quality gate checking
claude -p "Run all quality checks (TypeScript, linting, tests, build) and fix any issues before considering this task complete."

# Pre-commit validation
claude -p "Verify this code change compiles, passes all tests, and follows project patterns before we commit."
```

### Build Commands
```bash
[Auto-detect from package.json or project files]
npm run build          # Production build
npm run dev           # Development server
npm run test          # Run test suite
npm run lint          # Code linting
```

### Development Workflow
```bash
# Start development
npm run dev

# Run tests in watch mode  
npm run test:watch

# Type checking
npm run type-check

# Format code
npm run format

# Quality gate (run before committing)
npm run type-check && npm run lint && npm run test && npm run build
```

**Note**: Template commands above. Replace with actual project scripts during analysis.

## Claude Code Hooks & Automation

### Recommended Hooks Setup
```bash
# Post-task validation hook (add to .claude/hooks/)
#!/bin/bash
echo "Running post-task validation..."
npm run type-check && npm run lint && npm run test
if [ $? -eq 0 ]; then
    echo "✅ All quality checks passed"
else
    echo "❌ Quality checks failed - task not complete"
    exit 1
fi
```

### Automation Configuration
- **Pre-commit hooks** - Ensure code quality before commits
- **Continuous linting** - Real-time feedback on code issues  
- **Type checking integration** - Validate TypeScript on every change
- **Test automation** - Run relevant tests after modifications

For hooks setup guide: https://docs.anthropic.com/en/docs/claude-code/hooks-guide

## Communication Specificity Requirements

### Be Extremely Specific
- **File paths** - Always include exact file locations
- **Function/method names** - Reference specific code elements
- **Error messages** - Include complete error text
- **Expected behavior** - Describe precise desired outcomes
- **Constraints** - List all technical limitations or requirements

### Avoid Vague Requests
❌ "Fix the authentication"
✅ "Fix the JWT token validation in src/auth/middleware.ts where expired tokens are not being rejected properly"

❌ "Make the tests work"  
✅ "Fix the failing test in src/components/UserCard.test.tsx where the mock user object is missing the 'email' property"

❌ "Optimize performance"
✅ "Reduce the database query count in src/services/UserService.ts by implementing proper eager loading for user profiles"

## Environment Configuration

### Required Environment Variables
```bash
API_BASE_URL=https://api.example.com
DATABASE_URL=postgresql://...
JWT_SECRET=your-secret-key
```

### Development Setup
1. Clone the repository
2. Install dependencies: `npm install`
3. Copy `.env.example` to `.env.local`
4. Run development server: `npm run dev`

## Claude Code Integration Notes

### Best Practices for This Project
- Always run tests after making changes
- Use the existing component library before creating new components
- Follow the established API patterns in the services folder
- Update TypeScript types when modifying data structures

### Common Workflows
1. **Feature Development**: Describe the feature conversationally, I'll optimize into specific steps
2. **Bug Fixing**: Explain the issue as you see it, I'll investigate systematically
3. **Refactoring**: Request improvements generally, I'll propose specific implementation plans
4. **Testing**: Ask for test coverage, I'll write appropriate tests with clear structure

### Documentation Integration
The attached CSV file contains 784 entries of Claude Code documentation that can be referenced for:
- Advanced mechanics and optimization techniques
- Troubleshooting common issues
- Best practices from the community
- Integration patterns for enterprise environments

## Troubleshooting

### Common Issues & Solutions

#### **Build/Test Failures**
- **TypeScript errors**: Check actual type definitions vs assumed types
- **Test failures**: Verify mock objects match real interface signatures  
- **Import errors**: Ensure all dependencies are properly installed and available
- **Type mismatches**: Examine actual object properties vs what code assumes exists

#### **Claude Code Specific Issues**
- **Vague responses**: Provide more specific file paths and requirements
- **Wrong dependencies removed**: Ask for dependency analysis before removal
- **Poor refactoring**: Build context about existing patterns first
- **Test writing failures**: Examine existing test patterns before creating new ones

#### **Context & Communication Issues**
- **One-shot failures**: Break complex tasks into planned steps
- **Missing context**: Start with codebase analysis before making changes
- **Assumption errors**: Verify understanding before proceeding
- **Pattern violations**: Learn existing conventions before adding new code

### Recovery Strategies
```bash
# When things go wrong
claude -p "Let's start over. First analyze [specific files] to understand the current state, then create a step-by-step plan."

# For compilation issues
claude -p "Fix all TypeScript/compilation errors by examining the actual type definitions and ensuring our code matches them."

# For test issues  
claude -p "Examine the existing test setup and mocking patterns, then rewrite the failing tests to match the established patterns."
```

## Communication Guidelines

### For Effective Collaboration
- **Feel free to word vomit** - I'll help structure your thoughts
- **Don't worry about perfect prompts** - I'll optimize automatically  
- **Include any context you think might help** - file names, error messages, etc.
- **Ask for clarification** if my proposed approach doesn't seem right

### "OK, Go" Minimal Protocol
If you say **"OK, Go"**, I'll follow this script:
1. Greet you warmly
2. Ask: "What are you trying to build or improve with Claude Code?"
3. Encourage loose input: "Feel free to share screenshots, half-finished ideas, or messy thoughts."
4. Reassure: "You don't need perfect syntax—just describe what you want and I'll turn it into actionable steps."

### Session Documentation & Learning
- **End-of-session summaries** - Capture what was accomplished and learned
- **CLAUDE.md updates** - Suggest improvements to this file based on session learnings
- **Pattern recognition** - Note new project patterns discovered during work
- **Error documentation** - Record common failure modes and how to avoid them

### What I'll Always Do
- Detect when your request needs optimization
- **Plan before executing** - Create detailed implementation plans for approval
- Ask clarifying questions before proceeding
- **Validate at each step** - Ensure code compiles and tests pass
- Propose structured approaches with clear steps
- Confirm understanding before making changes
- Reference project patterns and maintain consistency
- **Document learnings** - Suggest CLAUDE.md improvements based on session work

## Additional Resources

### Claude Code Documentation
- Installation guide: [Reference from attached CSV]
- Configuration options: [Reference from attached CSV]
- Advanced mechanics: [Reference from attached CSV]
- Community best practices: r/ClaudeAI discussions

### Project-Specific Resources
- API documentation: [Your API docs]
- Design system: [Your design system]
- Deployment guide: [Your deployment process]

---

**Template Status**: This CLAUDE.md will auto-update once you start using Claude Code in this project.
**Manual Update**: Type `analyze this project and update CLAUDE.md` to trigger immediate analysis and customization.