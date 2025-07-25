Testing Prompt for Future Modules

Your goal is to create a test suite that is maintainable, meaningful, and aligned with the real code. Follow these guidelines when testing any new or existing module:
1. Understand Before You Test
    Read the actual function and class definitions
    Identify key inputs, outputs, and side effects
    Know what external modules/functions need mocking
    Clarify: is this logging, raising warnings, or both?

2. Apply Atomic Test Design
    One test file per function/class
    One test function per behavior or case
    No side effects between tests
    Prefer pure, predictable, and focused test logic

3. Use Modern pytest Patterns
    Use @pytest.mark.parametrize to cover multiple inputs efficiently
    Use tmp_path for file-related tests (instead of manual tempfile)
    Use pytest-mock or unittest.mock.patch to isolate dependencies
    Create fixtures for reusable test data or setup

4. Ensure Comprehensive Coverage
    Include normal, edge, and error cases
    Test unicode, long data, and malformed inputs when relevant
    Use realistic integration scenarios to validate full workflows
    Aim for high coverage (90%+) without chasing 100% blindly

5. Avoid Common Pitfalls
    Don’t guess behavior—check the implementation
    Don’t mock the wrong module path or object
    Don’t test assumptions that don’t reflect reality (e.g., expecting a warning when the code logs)
    Don't test logging
    Do test exceptions and validation logic deliberately

6. Make Tests Scalable and Useful
    Structure tests so they can grow independently
    Keep them fast and modular for quick debugging
    Make failures clear and isolated
    Treat tests as a form of documentation for how the code works

Why This Matters
This approach:
    Catches bugs before they reach users
    Helps document intent and behavior
    Makes onboarding easier for future developers
    Enables fast, confident iteration in a growing codebase
