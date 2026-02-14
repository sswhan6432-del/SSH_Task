"""
Environment Setup Verification Test
Tests that all v5.0 dependencies are correctly installed.

Run: python3 tests/test_environment.py
"""

import sys

def test_imports():
    """Test that all required packages can be imported."""
    print("Testing v5.0 environment setup...\n")

    tests = []

    # Test spaCy
    try:
        import spacy
        print(f"✅ spaCy {spacy.__version__} installed")
        tests.append(("spacy", True))
    except ImportError as e:
        print(f"❌ spaCy import failed: {e}")
        tests.append(("spacy", False))

    # Test spaCy English model
    try:
        import en_core_web_sm
        nlp = en_core_web_sm.load()
        doc = nlp("Test sentence for NLP processing.")
        print(f"✅ spaCy English model loaded ({len(doc)} tokens)")
        tests.append(("en_core_web_sm", True))
    except Exception as e:
        print(f"❌ spaCy model failed: {e}")
        tests.append(("en_core_web_sm", False))

    # Test transformers
    try:
        import transformers
        print(f"✅ transformers {transformers.__version__} installed")
        tests.append(("transformers", True))
    except ImportError as e:
        print(f"❌ transformers import failed: {e}")
        tests.append(("transformers", False))

    # Test scikit-learn
    try:
        import sklearn
        print(f"✅ scikit-learn {sklearn.__version__} installed")
        tests.append(("sklearn", True))
    except ImportError as e:
        print(f"❌ scikit-learn import failed: {e}")
        tests.append(("sklearn", False))

    # Test tiktoken
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode("Token counting test")
        print(f"✅ tiktoken installed ({len(tokens)} tokens counted)")
        tests.append(("tiktoken", True))
    except ImportError as e:
        print(f"❌ tiktoken import failed: {e}")
        tests.append(("tiktoken", False))

    # Test numpy
    try:
        import numpy as np
        arr = np.array([1, 2, 3])
        print(f"✅ numpy {np.__version__} installed")
        tests.append(("numpy", True))
    except ImportError as e:
        print(f"❌ numpy import failed: {e}")
        tests.append(("numpy", False))

    # Summary
    print("\n" + "="*50)
    passed = sum(1 for _, status in tests if status)
    total = len(tests)
    print(f"Environment Test Results: {passed}/{total} passed")

    if passed == total:
        print("✅ All dependencies installed successfully!")
        print("\n🚀 Ready for v5.0 implementation!")
        return 0
    else:
        print("❌ Some dependencies failed to install")
        failed = [name for name, status in tests if not status]
        print(f"Failed packages: {', '.join(failed)}")
        return 1

if __name__ == "__main__":
    sys.exit(test_imports())
