# pytr-Modified-

pytr-Modified- is an adjusted version of the original pytr API wrapper.  
It adds helper functions, improves module organization, and returns clean JSON data without formatted console output.

## Installation

```bash
pip install git+https://github.com/SoerenFox/pytr-Modified-.git
```

If the command `pytr` is not recognized after installation, add this to your PATH:  
`%APPDATA%\Python\Python312\Scripts` on Windows or `~/.local/bin` on Linux/macOS.

## Usage

```python
import pytr

client = pytr.Client()
data = client.get_positions()
print(data)
```

## Development

```bash
git clone https://github.com/SoerenFox/pytr-Modified-.git
cd pytr-Modified-
pip install -e .
```

## License

MIT License. See LICENSE file for details.
