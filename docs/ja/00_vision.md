# Vision

me-shower は単なる職務経歴書ジェネレーターではありません。

me-shower は、日々の仕事の痕跡、証跡、判断、学習、振り返りを通じて **Career Knowledge** を育てるための Personal Career Operating System です。

> Career Knowledge is the core.

me-shower の中心は Resume でも PDF でも Skills でもありません。中心に置くのは、自分の仕事と成長を長期的に支える構造化知識である Career Knowledge です。

> Resume is an output, not the source of truth.

Resume は重要な成果物ですが、正本ではありません。PDF も Timeline も Agent も Skills も、Career Knowledge を育てる、検証する、見せるための補助レイヤーまたは View です。

> A career is not written once. It grows through evidence, review, and reflection.

経歴は応募のたびにその場で作るものではなく、日々の仕事を通じて少しずつ育つものとして扱います。何をやったか、なぜそう判断したか、どこで学びがあったか、どの証跡がそれを支えるかを残し続けることで、後から再利用できる Career Knowledge になります。

## me-shower が目指すもの

me-shower が最適化したいのは、「それっぽい職務経歴書を早く出すこと」ではありません。仕事の実態に基づいた、長く使えるキャリア知識を育てることです。

- GitHub、Slack、Teams、Daily Report、local memo などに仕事の痕跡が残る
- その痕跡を証跡候補として扱う
- 証跡を review 可能な Canonical Event に整える
- Human Review を通ったものを Career Knowledge に近づける
- 必要になったときだけ Resume や PDF などの View を生成する

この順番を守ることで、応募先ごとに表現を変えても、元の事実と根拠はぶれにくくなります。

## なぜ Resume を中心にしないのか

Resume は相手と文脈に依存する出力です。応募先、役割、職種、強調したい経験によって表現や構成は変わります。

一方で Career Knowledge は、より上位にある長期的な土台です。同じ Career Knowledge から、将来的に次のような複数の View を作れます。

- Resume
- PDF
- GitHub Profile
- Portfolio
- Interview Stories
- Proposal Draft
- Skill Inventory
- Weekly Career Review
- Source Timeline

つまり me-shower は、ひとつの履歴書を作る道具というより、複数の出力を支える知識基盤を育てる道具です。

## AI と Human Review の役割

AI は Source を読み、構造化し、候補を提案し、View を作る補助をします。ただし、AI が提案したものをそのまま長期知識にしてはいけません。

誇張、機密の漏れ、誤抽出、根拠の弱い主張を止めるために Human Review が必要です。me-shower では、長期的に残す Career Knowledge への昇格は人間の確認を前提に考えます。

運用原則は次の一文で表せます。

```text
AI proposes.
Human reviews.
Career Knowledge persists.
```

## v0.x と v1.0.0 の考え方

v0.x は機能検証と学習の段階です。Source Intelligence、Evidence Guard、Confidence、Timeline、Review 境界の考え方が正しいかを試し、どこまでを concept として固定できるかを見極めます。

この段階では、一時的に `main.py` が大きくなったり、実装上の整理が後回しになったりしても構いません。優先するのは、Career Knowledge を中心に置いた責務境界が成立するかどうかです。

v1.0.0 では、その検証結果をもとにアーキテクチャを整理します。ただし、整理後も次の原則は崩しません。

- Career Knowledge を中心に置く
- Evidence を Claim より先に扱う
- View はあくまで下流の出力として扱う
- Human Review を永続知識化の前提にする

---
