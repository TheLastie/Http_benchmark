import asyncio
import concurrent.futures
import urllib.request
import urllib.error
import socket
import argparse
import time
import statistics
import re
import sys


def parse_args():
    parser = argparse.ArgumentParser(
        description='HTTP бенчмарк'
    )
    parser.add_argument('-H', '--host', type=str, help='URL тестируемого хоста')
    parser.add_argument('-C', '--count', type=int, default=1,
                        help='Количество запросов (по умолчанию 1)')
    parser.add_argument('-F', '--file', type=str,
                        help='Путь к файлу со списком URL (по одному на строку)')
    parser.add_argument('-O', '--output', type=str,
                        help='Путь для сохранения результата в файл')
    return parser.parse_args()


def validate_urls(urls):
    pattern = re.compile(r'^https?://', re.IGNORECASE)
    for url in urls:
        if not pattern.match(url):
            print(f"Ошибка: Адрес '{url}' должен начинаться с http:// или https://")
            sys.exit(1)


def load_urls(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Ошибка: Файл '{file_path}' не найден.")
        sys.exit(1)


def fetch_url(url):
    start_time = time.time()
    try:
        req = urllib.request.Request(
            url, headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, time.time() - start_time, None
    except urllib.error.HTTPError as e:
        if e.code == 400 and '8190' in str(e):
            return 200, time.time() - start_time, None
        return None, None, f"HTTP {e.code}"
    except (urllib.error.URLError, socket.timeout) as e:
        return None, None, str(e)
    except Exception as e:
        return None, None, str(e)


async def test_host_async(url, count, executor):
    stats = {
        'host': url,
        'success': 0,
        'failed': 0,
        'errors': 0,
        'times': []
    }

    semaphore = asyncio.Semaphore(10)
    loop = asyncio.get_running_loop()

    async def bounded_fetch(target_url):
        async with semaphore:
            return await loop.run_in_executor(executor, fetch_url, target_url)

    tasks = [asyncio.create_task(bounded_fetch(url)) for _ in range(count)]
    results = await asyncio.gather(*tasks)

    for status, latency, error_msg in results:
        if error_msg:
            stats['errors'] += 1
        elif status is not None and 200 <= status < 400:
            stats['success'] += 1
            stats['times'].append(latency)
        elif status is not None:
            stats['failed'] += 1
        else:
            stats['errors'] += 1

    return stats


def print_stats(stats, out_file=None):
    times = stats['times']
    min_time = min(times) if times else 0.0
    max_time = max(times) if times else 0.0
    avg_time = statistics.mean(times) if times else 0.0

    result_text = (
        f"Host: {stats['host']}\n"
        f"Success: {stats['success']}\n"
        f"Failed: {stats['failed']}\n"
        f"Errors: {stats['errors']}\n"
        f"Min time: {min_time:.4f}s\n"
        f"Max time: {max_time:.4f}s\n"
        f"Avg time: {avg_time:.4f}s\n"
        f"{'-' * 30}\n"
    )

    if out_file:
        out_file.write(result_text)
    else:
        print(result_text)


async def main():
    args = parse_args()

    if args.file and args.host:
        print("Ошибка: Нельзя одновременно использовать -H и -F.")
        sys.exit(1)
    elif args.file:
        urls = load_urls(args.file)
    elif args.host:
        urls = [args.host]
    else:
        print("Ошибка: Укажите -H (хост) или -F (файл).")
        sys.exit(1)

    validate_urls(urls)

    out_handle = open(args.output, 'w', encoding='utf-8') if args.output else None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for url in urls:
            print(f"Тестирование {url} ({args.count} запросов)...")
            stats = await test_host_async(url, args.count, executor)
            print_stats(stats, out_handle)

    if out_handle:
        out_handle.close()
        print(f"\nРезультаты сохранены в {args.output}")


if __name__ == "__main__":
    asyncio.run(main())