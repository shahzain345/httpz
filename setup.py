from setuptools import setup

if __name__ == "__main__":
    try:
        setup()
    except:  # noqa
        print(
            "\n\nAn error occurred during setup. Please make sure you have the latest version of setuptools and wheel."
            "\nPython 3.8 or later is required.\n"
            "If you have installed a Pythonic package manager like pip or conda, you can install them with:\n"
            "pip install -U setuptools wheel\n"
            "or\n"
            "conda install setuptools wheel\n"
        ) 