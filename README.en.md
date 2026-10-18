# HTTP Benchmark

[Русский](README.ru.md) | **English**

A dependency-free asynchronous Python command-line tool for sending requests to HTTP servers and recording benchmark results.

## Included in this repository

- `bchhttp.py` accepts a host URL, request count, an input file with URLs, and an optional output file.
- The Russian README documents the available CLI flags.

## Getting started

Run `python bchhttp.py -H https://example.com -C 10`. Use `-F path/to/urls.txt` to test a URL list and `-O results.txt` to save output.

## Notes

Use only against hosts you own or are authorized to test; tune request volume to avoid disrupting the service.
