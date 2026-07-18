# Repository Snapshot Tool

`build_snapshot.py`はImplementation Review、Release Gate、Repository Publish Handoff、Publish直前検証で共用する唯一のSnapshot Hash実装である。

## Canonical contract

- Git porcelain v2、current `HEAD` SHA、current working branchを入力にする。
- Pathはrepository-relative POSIX pathとし、path、old path順にsortする。
- File contentとbinaryは改行を正規化せずraw bytesをSHA-256でhashする。
- Symlinkはlink target bytes、submoduleはworking submodule HEAD object ID bytesをhashする。
- Deletedはmode/content hashを`null`、Renameはold/new path、Mode changeはmode、Untrackedはraw contentを記録する。
- ManifestはUTF-8 canonical JSON（sorted keys、compact separators、ASCII escapeなし、末尾改行なし）とする。
- `.git/`、`.codex/runtime/`、`.codex/tmp/`、`.codex/harness/development/artifacts/`を既定除外領域とする。
- 明示scope外の変更は`unexpected_files`へ返し、Publish Agentは`blocked`にする。

各SkillやAgentが独自のhash algorithmを実装してはならない。

```text
python .codex/tools/repository_snapshot/build_snapshot.py build --repository-root . --include path --output /tmp/snapshot.json
python .codex/tools/repository_snapshot/build_snapshot.py run-id --repository-id owner/repo --base-branch main --working-branch feat/x --checked-diff-hash <sha256> --handoff-revision 1
```
