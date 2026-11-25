#!/usr/bin/env python3
"""Minimal Alibaba Cloud RPC-style OpenAPI client (signature v1).

Reads credentials from ~/.workbench/config.json (never prints them).
Used as a fallback channel when Workbench shell sessions are exhausted.
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import uuid

CONFIG = os.path.expanduser("~/.workbench/config.json")


def creds():
    with open(CONFIG, "r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    prof = cfg["profiles"][cfg["current"]]
    return prof["access_key_id"], prof["access_key_secret"]


def pct(s):
    return urllib.parse.quote(str(s), safe="-_.~")


def call(action, params=None, version="2014-05-26", endpoint=None, method="GET", timeout=60):
    ak, sk = creds()
    region = (params or {}).get("RegionId", "cn-heyuan")
    endpoint = endpoint or "https://ecs.%s.aliyuncs.com" % region
    q = {
        "Action": action,
        "Version": version,
        "Format": "JSON",
        "AccessKeyId": ak,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureVersion": "1.0",
        "SignatureNonce": uuid.uuid4().hex,
        "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    q.update({k: v for k, v in (params or {}).items() if v is not None})
    canon = "&".join("%s=%s" % (pct(k), pct(q[k])) for k in sorted(q))
    sts = method + "&" + pct("/") + "&" + pct(canon)
    sig = base64.b64encode(
        hmac.new((sk + "&").encode(), sts.encode(), hashlib.sha1).digest()
    ).decode()
    q["Signature"] = sig
    url = endpoint + "/?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            return json.loads(body)
        except Exception:
            return {"_http": exc.code, "_body": body[:800]}


def run_shell(command, instance="i-f8zifsmhy00kro1q0pvw", region="cn-heyuan", timeout=120):
    """Execute a shell command through Cloud Assistant and return its output."""
    content = base64.b64encode(command.encode("utf-8")).decode()
    res = call("RunCommand", {
        "RegionId": region,
        "Type": "RunShellScript",
        "CommandContent": content,
        "ContentEncoding": "Base64",
        "InstanceId.1": instance,
        "Timeout": str(timeout),
        "Username": "root",
        "WorkingDir": "/root",
    })
    if "InvokeId" not in res:
        return {"error": res}
    invoke = res["InvokeId"]
    deadline = time.time() + timeout + 40
    while time.time() < deadline:
        time.sleep(2)
        out = call("DescribeInvocationResults", {
            "RegionId": region, "InvokeId": invoke, "InstanceId": instance,
        })
        try:
            item = out["Invocation"]["InvocationResults"]["InvocationResult"][0]
        except Exception:
            continue
        status = item.get("InvocationStatus") or item.get("InvokeRecordStatus")
        if status in ("Success", "Failed", "Error", "Timeout", "Stopped", "PartialFailed"):
            raw = item.get("Output", "")
            try:
                text = base64.b64decode(raw).decode("utf-8", "replace")
            except Exception:
                text = raw
            return {"status": status, "exit_code": item.get("ExitCode"),
                    "output": text, "invoke_id": invoke}
    return {"error": "poll timeout", "invoke_id": invoke}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "shell":
        print(json.dumps(run_shell(sys.argv[2]), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(call("DescribeCloudAssistantStatus", {
            "RegionId": "cn-heyuan", "InstanceId.1": "i-f8zifsmhy00kro1q0pvw",
        }), ensure_ascii=False, indent=2))
