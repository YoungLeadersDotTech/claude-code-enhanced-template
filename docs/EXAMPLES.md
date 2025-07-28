# Usage Examples

## Real-World Examples of Enhanced Claude Code

### Example 1: Bug Fix with Auto-Optimization

**Your input** (word vomit):
```
The login form is broken and users can't submit and I think it's something with validation or maybe the API call
```

**Claude's response**:
```
🔧 Let me help optimize this request

What I understood:
Login form submission is failing, possibly due to validation or API issues

I need to clarify:
1. Which login component file should I examine?
2. Are there console errors when users try to submit?
3. Is this happening for all users or specific scenarios?
4. Should I check both frontend validation and API integration?

Suggested approach:
1. Analyze the login form component and validation logic
2. Check API endpoint configuration and error handling
3. Test form submission with various input scenarios
4. Fix issues and verify with proper error messaging

Should I proceed with this approach?
```

### Example 2: Feature Development with Quality Gates

**Your input**:
```
Add a dark mode toggle to the app
```

**Claude's response**:
```
I'll add a dark mode toggle with proper theme management. Let me analyze your project first:

1. Checking existing styling approach...
2. Looking for theme management patterns...
3. Analyzing component structure...

Plan:
1. Create theme context with light/dark modes
2. Add toggle component with proper accessibility
3. Update existing components to use theme variables
4. Add user preference persistence
5. Test all components in both modes

Creating theme context in src/contexts/ThemeContext.tsx...

[Implements the feature step by step]

✅ Quality Gate Check:
- Code compiles: ✅
- Tests pass: ✅
- TypeScript validation: ✅
- Accessibility standards: ✅

Dark mode toggle is now complete and tested!
```

### Example 3: Refactoring with Context Building

**Your input**:
```
Refactor the user service to use TypeScript properly
```

**Claude's response**:
```
I'll refactor the user service for proper TypeScript usage. First, let me understand the current implementation:

1. Analyzing existing user service patterns...
2. Checking current type definitions...
3. Reviewing API integration approach...

Found issues:
- Missing interface definitions for User objects
- API responses aren't properly typed
- Error handling lacks type safety

Plan:
1. Define comprehensive User and API response interfaces
2. Add proper error type definitions
3. Update service methods with type guards
4. Ensure all return types are properly typed
5. Add JSDoc for better developer experience

Starting with interface definitions...

[Shows detailed refactoring steps]

✅ All TypeScript errors resolved
✅ Tests updated with proper type mocking
✅ Service now fully type-safe
```

### Example 4: Testing with Pattern Recognition

**Your input**:
```
Write tests for the shopping cart component
```

**Claude's response**:
```
I'll write comprehensive tests for the shopping cart. First, let me examine your existing test patterns:

Analyzing test structure:
- Using Jest + React Testing Library ✅
- Custom render helper for providers ✅
- Mock patterns for API calls ✅
- Accessibility testing included ✅

Following your project's test patterns:

```typescript
// ShoppingCart.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ShoppingCart } from './ShoppingCart';
import { CartProvider } from '../contexts/CartContext';
import { mockProducts } from '../__mocks__/products';

// Following your project's custom render pattern
const renderWithProvider = (component: React.ReactElement) => {
  return render(
    <CartProvider>
      {component}
    </CartProvider>
  );
};

describe('ShoppingCart', () => {
  // Tests follow your established patterns...
});
```

✅ Tests written following project conventions
✅ All edge cases covered
✅ Accessibility tests included
✅ Mock data matches your patterns
```

### Example 5: "OK, Go" Discovery Flow

**Your input**:
```
OK, Go
```

**Claude's response**:
```
👋 Hey there! Ready to code with Claude.

What are you trying to build or improve with Claude Code today?

Feel free to share screenshots, half-finished ideas, or messy thoughts. You don't need perfect syntax—just describe what you want and I'll turn it into actionable steps.

Some things I can help with:
- Building new features from scratch
- Debugging and fixing issues
- Refactoring and code improvements
- Writing tests and documentation
- Analyzing and understanding codebases

What's on your mind?
```

## Framework-Specific Examples

### React Project

**Auto-detected configuration**:
```markdown
## Project Overview
**Project Name**: My React Dashboard
**Main Technologies**: React, TypeScript, Tailwind CSS, Vite
**Purpose**: Customer analytics dashboard with real-time data visualization

## File Structure
src/
├── components/          # Reusable UI components
├── pages/              # Route-level components  
├── hooks/              # Custom React hooks
├── services/           # API integration
├── types/              # TypeScript definitions
└── __tests__/          # Test files
```

### Node.js API Project

**Auto-detected configuration**:
```markdown
## Project Overview
**Project Name**: E-commerce API
**Main Technologies**: Node.js, Express, TypeScript, PostgreSQL, Prisma
**Purpose**: RESTful API for e-commerce platform with authentication and payments

## File Structure
src/
├── controllers/        # Route handlers
├── middleware/         # Express middleware
├── models/            # Database models
├── routes/            # API routes
├── services/          # Business logic
└── utils/             # Helper functions
```

### Python Project

**Auto-detected configuration**:
```markdown
## Project Overview
**Project Name**: ML Pipeline
**Main Technologies**: Python, FastAPI, SQLAlchemy, Pandas, Scikit-learn
**Purpose**: Machine learning pipeline for predictive analytics

## File Structure
src/
├── api/               # FastAPI routes
├── models/            # ML models
├── data/              # Data processing
├── utils/             # Helper functions
└── tests/             # Test files
```

## Advanced Workflows

### Complex Feature Development

**Input**: "Build a real-time chat system"

**Claude's approach**:
1. **Requirements gathering** - Asks about authentication, persistence, scaling needs
2. **Architecture planning** - Proposes WebSocket vs Server-Sent Events approach  
3. **Implementation phases** - Breaks into backend, frontend, and integration steps
4. **Quality assurance** - Tests real-time functionality, handles edge cases
5. **Documentation** - Creates API docs and usage examples

### Large Codebase Refactoring

**Input**: "Modernize this legacy React class components to hooks"

**Claude's approach**:
1. **Codebase analysis** - Maps component dependencies and state usage
2. **Migration strategy** - Plans incremental conversion approach
3. **Pattern establishment** - Creates reusable hook patterns
4. **Systematic conversion** - Converts components while maintaining functionality
5. **Testing verification** - Ensures behavior remains identical

### Performance Optimization

**Input**: "The app is slow, make it faster"

**Claude's approach**:
1. **Performance analysis** - Identifies bottlenecks and measurement strategies
2. **Priority ranking** - Focuses on highest-impact optimizations first
3. **Implementation** - Adds memoization, lazy loading, code splitting
4. **Measurement** - Verifies improvements with actual metrics
5. **Documentation** - Records optimization techniques for team

## Tips for Better Results

### 1. Be Specific About Context
❌ "Fix the bug"
✅ "Fix the bug in src/components/UserCard.tsx where expired user sessions show wrong status"

### 2. Include Error Messages
❌ "Tests are failing"
✅ "Tests are failing with 'TypeError: Cannot read property email of undefined' in UserCard.test.tsx"

### 3. Mention Constraints
❌ "Add authentication"
✅ "Add JWT authentication that works with our existing Express middleware and PostgreSQL user table"

### 4. Describe the Goal
❌ "Refactor this code"
✅ "Refactor the user service to be more testable and follow our TypeScript conventions"

### 5. Reference Existing Patterns
❌ "Write a new component"
✅ "Write a new component following the same patterns as our existing Card components in src/components/"

## Common Scenarios

### 🚨 Emergency Bug Fix
**Best approach**: Start with exact error messages and affected files. Claude will prioritize quick fixes with proper testing.

### 🏗️ New Feature Development
**Best approach**: Describe the user story and business requirements. Claude will plan architecture and break into phases.

### 🔧 Code Quality Improvement
**Best approach**: Mention specific quality goals (performance, maintainability, testing). Claude will analyze and prioritize improvements.

### 📚 Learning and Exploration
**Best approach**: Ask "explain" and "analyze" questions. Claude will provide educational context while making changes.

### 🔄 Technical Debt Reduction
**Best approach**: Point to specific pain points or outdated patterns. Claude will modernize while maintaining functionality.

Remember: The enhanced template makes Claude Code much more reliable and context-aware, but clear communication still makes the biggest difference! 🚀