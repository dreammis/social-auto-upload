"""通过 sau CLI 发布微信公众号图文的最小模板。

用法：python wechat_cli_template.py --account creator --title "标题" --content-file article.md --prepare-only
移除 --prepare-only 会进入真实发表流程；发表最后一步需管理员微信扫码验证。
"""
import argparse
import json
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--content-file", required=True)
    parser.add_argument("--digest")
    parser.add_argument("--cover")
    parser.add_argument("--originality", choices=("none", "original"), default="none")
    parser.add_argument("--no-broadcast", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()

    command = ["sau", "wechat", "upload-article", "--account", args.account,
               "--title", args.title, "--content-file", args.content_file,
               "--originality", args.originality]
    if args.digest:
        command += ["--digest", args.digest]
    if args.cover:
        command += ["--cover", args.cover]
    if args.no_broadcast:
        command.append("--no-broadcast")
    if args.prepare_only:
        command.append("--prepare-only")

    completed = subprocess.run(command, text=True, capture_output=True)
    print(completed.stdout)
    if completed.returncode:
        print(completed.stderr)
        raise SystemExit(completed.returncode)
    # 结果 JSON 也为每行前缀，如需结构化处理可逐行解析。
    for line in reversed(completed.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            print("result:", json.loads(line).get("status"))
            break


if __name__ == "__main__":
    main()
