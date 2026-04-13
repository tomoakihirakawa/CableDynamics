# cable — Cable / mooring line dynamics solver

質点ばねモデルによるケーブル動力学 C++ ソルバと、その入出力を包む Python GUI
一式。BEM 本体 ([lib/include/Network.hpp](../lib/include/Network.hpp),
[lib/include/LumpedCable.hpp](../lib/include/LumpedCable.hpp)) の派生クラスとして
実装され、共有メッシュ/積分インフラを流用する。

## 目的

- **浮体式海洋構造物の係留索解析** — 大変形カテナリ、touchdown、張力評価。
  ISO19901-7 (2013) 相当の諸元（R4 チェーン 132 mm, 1.4 GN 剛性 等）を初期
  想定。複数本の係留索を 1 つの `LumpedCableSystem` で一括管理する。
- **斜張橋ケーブル解析への流用** — 橋梁ケーブルの独立平衡形状。複数本を
  まとめて 1 回の CLI 呼び出しで解ける（多重ライン入力）。風応答（VIV、
  ギャロッピング、バフェッティング）は未対応 ([TODO](#todo) 参照)。
- **BEM 時間領域ソルバ側との接続** — `LumpedCable` は `Network` 派生なので、
  同じ RK4 時間積分インフラで浮体 BEM と連成する。`CableAttachment::BodyFrame`
  で端点を浮体フレームに追従させ、`LumpedCableSystem::advanceRKStage` /
  `commitRKStep` を BEM 側時間ループから呼び出す構成。

## 実装内容

### クラス階層

2026-04-12 のリファクタで次の構成に落ち着いた。すべて
[lib/include/LumpedCable.hpp](../lib/include/LumpedCable.hpp) に集約。

| 型 | 役割 |
|---|---|
| `LumpedCable` | 1 本の集中質量ケーブル（旧 `MooringLine` の後継）。`Network` 派生 |
| `CableProperties` | POD: `mass_per_length`, `EA`, `damping`, `diameter`, `EI=0`（将来用） |
| `CableAttachment` | 端点の拘束種別 `{WorldFixed, BodyFrame}` + オフセット。浮体追従時は `Network* body` と world/body pose から端点位置を計算 |
| `LumpedCableSystem` | 複数の `LumpedCable` を束ねる。`addCable()`, `solveEquilibrium()`, `advanceRKStage()/commitRKStep()`, `forceOnBody()` |

`using MooringLine = LumpedCable;` のエイリアスが同ヘッダ末尾で提供されて
いるので、旧 `MooringLine` を参照する古いコードは変更なしで通る。

### ディレクトリ構成

| パス | 内容 |
|---|---|
| [cable_solver.cpp](cable_solver.cpp) | メイン CLI ソルバ。単一ライン・多重ライン両方の JSON を受け付ける |
| [build_solver/](build_solver/) | `cable_solver` バイナリのビルドツリー |
| [gui/](gui/) | PySide6 + PyVista 製 GUI (`pycable` パッケージ) |
| [gui/examples/mooring_3leg_catenary.json](gui/examples/mooring_3leg_catenary.json) | 公開用 3 本脚カテナリ係留サンプル（多重ライン形式） |
| [examples/yuri_bridge/](examples/yuri_bridge/) | 単一主塔 2D 斜張橋 C01–C12 の入力 JSON と Excel 原データ（dev only、公開同期対象外） |
| [memo.md](memo.md) | ISO19901-7 係留諸元、橋梁ケーブル風応答への拡張検討メモ |
| [references/](references/) | 文献資料 |

### ビルド

ルート CMakeLists からトップダウンで作る。

```bash
cd cable/build_solver
cmake -DCMAKE_BUILD_TYPE=Release -DSOURCE_FILE=cable/cable_solver.cpp ../..
make -j$(sysctl -n hw.logicalcpu)
```

生成物は [build_solver/cable_solver](build_solver/cable_solver)。
GUI の `solver_discovery.py` はこのパスを自動検出する。

### CLI

```bash
./cable_solver input.json output_dir/
```

入力 JSON のフォーマットを自動判定して処理する。検出順:

1. `input_files` キーあり → **settings mode**（複数ケーブルファイルを参照）
2. `end_a_position` キーあり → **per-cable format**（新しい標準形式）
3. `mooring_*` / `cable_*` 13 要素配列あり → **多重ライン形式**（BEM 互換）
4. `point_a` キーあり → **単一ライン形式**（レガシー）

#### 出力先

結果は `output_dir/` に書かれる:

| 形式 | 出力ファイル |
|---|---|
| per-cable | `output_dir/<name>_result.json` |
| settings mode | `output_dir/<name>_result.json` （各ケーブルごと） |
| 多重ライン | `output_dir/result.json`（全ケーブルをまとめた 1 ファイル） |
| 単一ライン | `output_dir/result.json` |

GUI 経由の場合、結果は `~/.cache/pycable/runs/<timestamp>/` に自動保存される（`File → Set output directory` で変更可）。`input.json` も同ディレクトリにコピーされるため、History から完全に復元できる。

#### SNAPSHOT

実行中は stdout に SNAPSHOT 行が流れる（GUI がリアルタイム 3D 更新に使用）。

- 単一 / per-cable: `SNAPSHOT {"iter":N,"norm_v":...,"positions":[...]}`
- 多重ライン: `SNAPSHOT {"iter":N,"cable":"L01","norm_v":...,"positions":[...]}`
- 動的モード: `SNAPSHOT {"t":0.01,"iter":N,"positions":[...]}`

### 入力 JSON schema

#### Per-Cable 形式（推奨）

1 ケーブル = 1 JSON ファイル。ケーブルが自分の端点位置・材料特性・初期条件を自己完結で持つ。

```json
{
  "name": "C01",
  "end_a_position": [-104.1, 0.0, 0.0],
  "end_b_position": [0.0, 0.0, 45.0],
  "end_a_body": "deck",
  "end_b_body": "tower",
  "initial_condition": "tension",
  "tension_top": 1019998,
  "tension_bottom": 986767,
  "cable_length": 113.41,
  "n_points": 31,
  "line_density": 63.2514,
  "EA": 1530925000.0,
  "damping": 0.5,
  "diameter": 0.10129,
  "output_directory": "./output",
  "gravity": 9.81,
  "mode": "equilibrium"
}
```

| Key | 必須 | Default | 意味 |
|---|---|---|---|
| `name` | いいえ | ファイル名 stem | ケーブル名 |
| `end_a_position` | **はい** | — | 端点 A の world 位置 [x, y, z] |
| `end_b_position` | **はい** | — | 端点 B の world 位置 [x, y, z] |
| `end_a_body` | いいえ | — | BEM 連携用 body ラベル |
| `end_b_body` | いいえ | — | BEM 連携用 body ラベル |
| `initial_condition` | いいえ | `"length"` | `"length"`: cable_length = 自然長。`"tension"`: 目標張力から自然長を反復で逆算 |
| `tension_top` | tension 時 | — | 上端の目標張力 [N] |
| `tension_bottom` | tension 時 | — | 下端の目標張力 [N] |
| `cable_length` | **はい** | — | `"length"` 時は自然長、`"tension"` 時はコード長（参照用） |
| `n_points` | **はい** | — | 節点数 (= n_segments + 1) |
| `line_density` | **はい** | — | kg/m |
| `EA` | **はい** | — | 軸剛性 [N] |
| `damping` | いいえ | 0.5 | N·s/m |
| `diameter` | いいえ | 0.132 | [m] |
| `output_directory` | いいえ | — | 結果出力先（GUI が読み取り） |
| `gravity` | いいえ | 9.81 | m/s² |
| `mode` | いいえ | `"equilibrium"` | `"equilibrium"` / `"dynamic"` |
| `end_a_motion` | いいえ | `"fixed"` | 端点の運動（dynamic 用） |
| `end_b_motion` | いいえ | `"fixed"` | `"fixed"` / `"sinusoidal"` |
| `end_b_motion_dof` | sinusoidal 時 | — | `"surge"` / `"sway"` / `"heave"` |
| `end_b_motion_amplitude` | sinusoidal 時 | — | 振幅 [m] |
| `end_b_motion_frequency` | sinusoidal 時 | — | 周波数 [Hz] |
| `dt` | dynamic 時 | — | 時間刻み [s] |
| `t_end` | dynamic 時 | — | 終了時刻 [s] |

#### 初期条件: 自然長 vs 張力

- **`"initial_condition": "length"`**（デフォルト）: `cable_length` をそのまま自然長として使う
- **`"initial_condition": "tension"`**: `tension_top` / `tension_bottom` を目標値として secant method で自然長を反復収束させる。両端張力の RMS 誤差を最小化。実橋のように自然長が不明で張力のみ既知の場合に使用

#### settings.json（複数ケーブルの一括指定）

BEM の `settings.json` → `input_files` と同じパターン。

```json
{
  "input_files": ["cables/C01.json", "cables/C02.json", "cables/C12.json"],
  "output_directory": "./output",
  "gravity": 9.81,
  "mode": "equilibrium",
  "max_equilibrium_steps": 500000,
  "equilibrium_tol": 0.01,
  "snapshot_interval": 5000
}
```

- `input_files` の各パスは settings.json からの相対パスで解決
- settings の共通パラメータは各ケーブル JSON のデフォルトとして適用（ケーブル側に同キーがあればそちらが優先）
- 各ケーブルは独立に解かれ、結果は `output_dir/<name>_result.json` として個別生成

#### 動的モード（prescribed motion）

端点に強制振動を与え、ケーブルの時間応答を解く:

```json
{
  "name": "D01",
  "end_a_position": [500.0, 0.0, -58.0],
  "end_b_position": [0.0, 0.0, 0.0],
  "end_b_motion": "sinusoidal",
  "end_b_motion_dof": "heave",
  "end_b_motion_amplitude": 2.0,
  "end_b_motion_frequency": 0.05,
  "cable_length": 522.0,
  "n_points": 41,
  "line_density": 348.5,
  "EA": 1400000000.0,
  "mode": "dynamic",
  "dt": 0.005,
  "t_end": 20.0,
  "output_interval": 0.1
}
```

動的結果 JSON には時系列の張力が含まれる:

```json
{
  "name": "D01",
  "mode": "dynamic",
  "n_output_steps": 201,
  "time": [0.0, 0.1, 0.2, ...],
  "top_tension": [T0, T1, ...],
  "bottom_tension": [T0, T1, ...],
  "positions_final": [[x,y,z], ...],
  "computation_time_ms": 648.0
}
```

内部では CFL 安定条件 ($\Delta t_\text{cfl} = L_0 / \sqrt{EA/\rho}$) でサブステップを自動分割し、ユーザ指定の `dt` が CFL を超えても安定に計算する。

#### 単一ライン形式（レガシー）

すべてのキーはオプション（省略時はデフォルト適用）。

| Key | Default | Unit | 備考 |
|---|---|---|---|
| `point_a` | `[500, 0, -58]` | m | 端点 A（アンカー想定） |
| `point_b` | `[0, 0, 0]` | m | 端点 B（フェアリード想定） |
| `cable_length` | `522` | m | 自然長の合計 |
| `n_segments` | `40` | — | 分割数、節点数は +1 |
| `line_density` | `348.5` | kg/m | 単位長あたり**質量**（旧引数名 `density` は同値。`weight_per_unit_length` という内部メンバ名も kg/m 扱い） |
| `EA` | `1.4e9` | N | 軸剛性 |
| `damping` | `0.5` | N·s/m | `networkLine::damping`（隣接節点間相対速度に作用） |
| `diameter` | `0.132` | m | 抗力射影面積計算用 |
| `gravity` | `9.81` | m/s² | 正値で与える（向きは内部で -z） |
| `mode` | `"equilibrium"` | — | 現状は `equilibrium` のみ受け付け |
| `max_equilibrium_steps` | `500000` | — | 上限ステップ数 |
| `equilibrium_tol` | `0.01` | m/s | 収束判定閾値（節点最大速度） |
| `snapshot_interval` | `10000` | — | SNAPSHOT 出力間隔 |

#### 多重ライン形式（BEM 互換）

`mooring_<name>` または `cable_<name>` をキーに、13 要素のフラット配列を値
として与える。1 個でも存在すれば多重ラインモードに切り替わる。

```json
{
  "mooring_L01": [
    "L01",
    500.0, 0.0, -58.0,
    0.0, 0.0, 0.0,
    522.0,
    41,
    348.5,
    1.4e9,
    0.5,
    0.132
  ],
  "mooring_L02": ["L02", ...],
  "gravity": 9.81,
  "mode": "equilibrium",
  "max_equilibrium_steps": 500000,
  "equilibrium_tol": 0.01,
  "snapshot_interval": 10000
}
```

配列要素の順序は
`[name, ax, ay, az, bx, by, bz, total_length, n_points, line_density, EA, damping, diameter]`。
`n_points` は節点数（= `n_segments + 1`）。これは BEM 側
[bem/core/BEM_inputfile_reader.hpp](../bem/core/BEM_inputfile_reader.hpp) の `mooring_*`
パーサと**完全に一致**するので、BEM 係留入力をそのまま `cable_solver` でも
静的平衡確認用に解ける。

トップレベルの `gravity` 等の共通スカラは単一ライン形式と同じ。

### 出力 `result.json`

#### 単一ライン形式

| Key | Type | 意味 |
|---|---|---|
| `n_nodes` | int | 節点数 |
| `positions` | `[[x,y,z], ...]` | 最終節点座標 |
| `tensions` | `[T_0, ..., T_{n-1}]` | 節点張力（隣接 2 セグメントの平均） |
| `top_tension` | float | 末尾セグメントの張力 |
| `bottom_tension` | float | 先頭セグメントの張力 |
| `max_tension` | float | 全セグメント張力の最大値 |
| `converged` | bool | 収束時 `true`、`max_equilibrium_steps` 到達で `false` |
| `computation_time_ms` | float | ソルバ経過時間 |

#### 多重ライン形式

```json
{
  "n_cables": 3,
  "converged": true,
  "computation_time_ms": 524.0,
  "cables": {
    "L01": { "n_nodes": 41, "positions": [...], "tensions": [...],
             "top_tension": ..., "bottom_tension": ..., "max_tension": ... },
    "L02": { ... },
    "L03": { ... }
  }
}
```

各ケーブル名をキーとする辞書の中に、単一ライン形式と同じフィールドが入る。

### 例題

| 例題 | 場所 | 形式 | 内容 |
|---|---|---|---|
| 標準カテナリ 522 m | [gui/examples/catenary_500m.json](gui/examples/catenary_500m.json) | 単一 | ISO19901-7 相当チェーン、深さ 58 m |
| 橋梁ケーブル小例 | [gui/examples/bridge_cable_small.json](gui/examples/bridge_cable_small.json) | 単一 | GUI 用の軽量テスト |
| 橋梁ケーブル C01 | [gui/examples/bridge_C01.json](gui/examples/bridge_C01.json) | per-cable | 斜張橋 C01、body ラベル付き |
| 3 本脚カテナリ係留 | [gui/examples/mooring_3leg_catenary.json](gui/examples/mooring_3leg_catenary.json) | 多重 | 120° 分散の 3 本脚 |
| 端点 heave 振動 | [gui/examples/dynamic_heave.json](gui/examples/dynamic_heave.json) | per-cable | 動的モード、片端 sinusoidal |
| 斜張橋 12 本一括 | [examples/yuri_bridge/settings.json](examples/yuri_bridge/settings.json) | settings | 12 本 per-cable + tension 初期条件（dev only） |

## モデル方法

### データ構造

`LumpedCable` は `Network` の派生クラス
([LumpedCable.hpp](../lib/include/LumpedCable.hpp))。生成時に端点 A, B の間を
等分割して `networkPoint` と `networkLine` を張り、
`total_length / n_segments` を各 `networkLine::natural_length` に設定する。

`setDensityStiffnessDampingDiameter(double mass_per_length, ...)` で
`weight_per_unit_length`, `stiffness`, `damping`, `diameter` を全 line に設定し、
各節点の質量を $m_i = \tfrac12(L_{i-1}+L_i)\,\rho_\text{line}$ として算出する。
先頭・末尾節点の質量は半分になる。

> Note: メンバ名 `weight_per_unit_length` は歴史的経緯で「重量」と名乗るが、
> 実態は**単位長あたり質量** [kg/m] である。2026-04-12 のリファクタで引数名
> は `density` → `mass_per_length` に統一した。メンバ名の統一は後日。

### 節点力（[Network.hpp](../lib/include/Network.hpp)）

1. **張力 `getTension()`**
   - 弾性項（引張のみ）:
     $\vec F_\text{el} = EA \cdot \max(0, \varepsilon) \cdot \hat{\Delta x}$,
     $\varepsilon = (|\Delta x| - L_0)/L_0$
   - 隣接節点間の相対速度に対する粘性項:
     $\vec F_\text{damp} = -c_l \, (\vec v_i - \vec v_j)$
     ($c_l$ は `networkLine::damping`、材料粘性として働く)
   - 圧縮時 ($\varepsilon < 0$) は弾性項ゼロ、粘性項のみ残る。

2. **抗力 `getDragForce(Cd)`**
   - 流体密度は `_WATER_DENSITY_` ハードコード、流体速度は `{0,0,0}` 固定。
     現状は水中静止流体中のケーブルしか扱えない。
   - 節点速度の接線垂直成分から
     $\vec F_d = \tfrac12 \rho_w |v_\perp|^2 \, C_d \, A_\text{proj} \, \hat v_\perp$
     を計算する。

3. **重力** — $\vec F_g = m_i \, g \, (0,0,-1)$。

### 時間積分

#### `LumpedCable::step(t, dt, BC)` — 純粋な RK4 1 ステップ

dt ランプや stdout 出力を持たない薄い 1 ステップ進行関数。BEM 時間ループ
(`LumpedCableSystem::advanceRKStage`) から RK ステージ毎に呼ばれる。

#### `LumpedCable::simulate(t, dt, BC, silent=false)` — warmup 付き

step 数に応じた dt ランプ（最初の 10/100/1000 ステップを細かくする）を
持つ。旧 `MooringLine::simulate` と完全互換。`silent=true` で stdout を
抑制できる。

#### `LumpedCable::setEquilibriumState(BC, tol=1e-3, max_iters=100)`

`DragForceCoefficient` を RAII guard で一時的に 1000 まで持ち上げ、
`simulate` をループ呼び出しして静的平衡を探索する。収束判定
`norm_total_velocity < tol` が効いており（以前はコメントアウトされていた）、
収束したら `true` を返して早期終了する。

#### `LumpedCableSystem::solveEquilibrium(tol, max_steps, snapshot_interval, snapshot_cb)`

`cable_solver.cpp` が旧来持っていた自前の RK4 疑似緩和ドライバを System 側
に移植したもの。特徴:

- **ケーブルごとの CFL dt**: 各ケーブルの
  $\Delta t_\text{cfl} = L_0 / \sqrt{EA/\rho_\text{line}}$ を個別に保持し、
  それぞれの固有タイムスケールで進める。
- **ケーブルごとの収束ロック**: 1 本ずつ `max|v| < tol && step > 1000` を
  満たした時点でそのケーブルの積分を停止する。全本ロックで外側ループ終了。
  これにより 12 本混在系でも、個別に解いた結果と数値誤差レベル（< 0.005 N）
  で一致する。
- **snapshot コールバック**: `(iter, max_vel, positions_by_name)` を
  `snapshot_interval` ごとに呼ぶ。pycable の live 3D 更新のインタフェース。
- **Cd = 1000 の RAII guard**: 例外で途中終了しても元の抗力係数に戻る。

#### `LumpedCableSystem::advanceRKStage(t, dt) / commitRKStep()`

BEM 時間ループの各 RK ステージごとに呼ぶ 2 段階 API。
`advanceRKStage` は各 `CableAttachment` から現 RK 段での fairlead 位置を
`currentWorldPosition()` / `nextWorldPosition(dt)` で取得し、各 cable に対し
`step(t, dt, BC)` を 1 回呼ぶ。`commitRKStep` は `net->RK_Q.finished` が
true のときに `p->X`, `p->velocity` へ RK サブ状態を反映する。

`CableAttachment::nextWorldPosition(dt)` は旧 `nextPositionOnBody()` の
3 分岐（SoftBody / `relative_velocity` / RigidBody + `isFixed` 軸別固定）を
そのまま移植しているので、BEM 既存挙動と完全一致する。

#### `LumpedCableSystem::forceOnBody(body) → (F, T)`

指定 `body` に `BodyFrame` で取り付いた全ケーブルの fairlead 合力・合モー
メントを返す。`end_a` / `end_b` どちらでも対応できる対称実装。BEM
[bem/core/BEM_solveBVP.hpp](../bem/core/BEM_solveBVP.hpp) の力フィードバック
に使う。

### 現在の物理モデルの制約

- 曲げ剛性 $EI$ なし（純粋な string モデル）。将来用のフィールド
  `CableProperties::EI = 0` だけ先行で置いてある。橋梁ケーブルの端部応力・
  疲労評価には不十分。
- 空気密度を使った空力なし（`_WATER_DENSITY_` ハードコード）。
- 流体速度は 0 固定（海流、風速プロファイル、乱流入力いずれも未実装）。
- 構造減衰は隣接節点間相対速度（材料粘性）のみ。
- 動的モード (`mode: "dynamic"`) は sinusoidal prescribed motion のみ。時系列入力やモーダル変形は未実装。

## GUI について

`pycable` — PySide6 + PyVista 製の薄い GUI。物理は一切持たず、`cable_solver`
バイナリを叩くフロントエンドに徹する。詳細は [gui/README.md](gui/README.md)。

![pycable GUI — 斜張橋 12 本ケーブルの張力分布](docs/gui_yuri_bridge_12cables.png)

*斜張橋（ゆり橋）の 12 本ケーブルを settings.json から一括ロードし Run All で解いた結果。全ケーブルの張力を共通のカラースケール（viridis）で表示。左パネルに Lines list（C01–C12）、パラメータフォーム（Initial condition: tension 対応）、Run / Stop / Run All ボタン。下部に Log / History タブ。*

### データモデル

- `CableParams` — 単一ケーブルのレガシー入力形式
- `CableSpec` — BEM 互換フラット配列形式（13 要素）
- `LumpedCableSystemParams` — 複数ケーブル + 共通スカラ。settings.json / per-cable / 多重ライン / 単一ラインの全形式を自動判定して読み込み
- `PerCableParams` — 新 per-cable JSON 形式。`initial_condition`, `tension_top/bottom`, `end_a_body/end_b_body`, `end_a_motion/end_b_motion` を含む

### 機能

1. **File → Open input JSON** で全形式を受け付け（settings.json, per-cable, 多重ライン, 単一ライン）。settings.json を開くと参照先の全ケーブルがロードされる
2. **Lines list** でロードされたケーブル一覧を表示、選択中の 1 本を下段フォームで編集
3. **Initial condition** ドロップダウン: `length`（自然長直接指定）/ `tension`（目標張力から逆算）の切替。tension 選択時は Tension top / Tension bottom フィールドが活性化
4. **Run ボタン** — 選択中 1 本を解く
5. **Run All ボタン** — 全ケーブルを一括実行。結果は共通テンションカラーマップで 3D 表示（全ケーブルの張力範囲を統一したスケールバー付き）
6. **File → Set output directory** で結果の永続保存先を指定。未指定時は `~/.cache/pycable/runs/<timestamp>/` に自動保存
7. **File → Recent files** — 最近開いた 10 ファイルを記憶（QSettings 永続化）
8. **History タブ**（下部ドック）— 過去の実行結果を記録。ケース名・張力・時刻を表示。ホバーで詳細（パス、収束状態、計算時間）。**Load ボタン**で結果を再表示 + 入力パラメータを復元（同ディレクトリの `input.json` から完全復元）

### 場所とソルバ探索

- **Dev tree**: [cpp/cable/gui/](gui/) ← 真実の源泉。ここを編集する。
- **Public tree**: `~/CableDynamics/cable/gui/` は dev から
  [sync_all_public.sh](../sync_all_public.sh) で一方向 rsync。直接編集しない。
- `solver_discovery.py` の探索順:
  1. `$PYCABLE_SOLVER_PATH`（環境変数で強制指定）
  2. `$CABLE_DYNAMICS_ROOT/build/cable_solver`
  3. `<cable>/build_solver/cable_solver` (dev レイアウト)
  4. `<cable>/../build/cable_solver` (public レイアウト)
  5. `~/CableDynamics/build/cable_solver`
  6. `which cable_solver`

### 起動

```bash
cd gui
./run.sh
```

初回は `.venv` を作成して `pip install -e .` を走らせ、2 回目以降は同じ
venv を再利用する。

### パッケージ pin

| パッケージ | 制約 | 理由 |
|---|---|---|
| PySide6 | `<6.10` | 6.10.x は `QSplashScreen.show()` ハング・`eventFilter` 再帰 |
| vtk | `==9.3.1` | 9.6+ は Python 3.12 on macOS で import ハング |
| PyVista | `0.43.x` | VTK 9.3.1 と互換 |

### テスト

```bash
cd gui && source .venv/bin/activate
pytest tests/ -v
```

- [tests/test_params.py](gui/tests/test_params.py) — `CableParams` シリアライズ
- [tests/test_system_params.py](gui/tests/test_system_params.py) — `LumpedCableSystemParams` の単一・多重・per-cable・settings 往復
- [tests/test_per_cable_params.py](gui/tests/test_per_cable_params.py) — `PerCableParams` round-trip、legacy 変換
- [tests/test_bridge.py](gui/tests/test_bridge.py) — subprocess ブリッジ層
- [tests/test_solver_discovery.py](gui/tests/test_solver_discovery.py) — バイナリ探索
- [tests/test_integration.py](gui/tests/test_integration.py) — 実バイナリ必須
- [tests/test_bridge_lifecycle.py](gui/tests/test_bridge_lifecycle.py) — 実バイナリ必須

## BEM との連成

BEM 時間領域ソルバ ([bem/time_domain/main_time_domain.cpp](../bem/time_domain/main_time_domain.cpp))
は `Network::cable_system` (`std::unique_ptr<LumpedCableSystem>`) を介して
係留索を扱う。要点:

1. 入力 JSON の `mooring_*` キーを
   [bem/core/BEM_inputfile_reader.hpp](../bem/core/BEM_inputfile_reader.hpp) が
   `cable_system->addCable()` に渡す。端点 A は `CableAttachment::worldFixed`、
   端点 B は `CableAttachment::onBody(floating_body, X_end)`。
2. 全ライン入力が済んだ後、`cable_system->solveEquilibrium()` で初期静的
   平衡を求める。これは `cable_solver` と同じ疑似緩和ドライバ。
3. 時間ループ内では BEM の各 RK ステージで
   `cable_system->advanceRKStage(t, dt)` を呼び、`RK_Q.finished` で
   `commitRKStep()` する。
4. 浮体力の BVP では `cable_system->forceOnBody(body)` が合力・合モー
   メントを返し、並進・回転 BIE に足される。

この構成により、`cable_solver` での橋梁ケーブル静的平衡計算と、BEM 内部の
浮体係留時間積分が**同じコード**を共有する。

## 変更履歴

- **2026-04-13**: per-cable JSON 形式（1 ケーブル = 1 ファイル）と settings.json
  を導入。`initial_condition: "tension"` で目標張力から自然長を secant method で
  反復収束する機能を追加（RMS 評価）。動的モード（`mode: "dynamic"`）で端点に
  sinusoidal prescribed motion を指定可能に（CFL sub-stepping 付き）。GUI に
  Run All ボタン（共通テンションカラーマップ）、Recent Files メニュー、Run History
  （永続化 + Load 復元）、output directory 設定、初期条件 UI を追加。
  `cable_common/` 共有パッケージを作成し BEM GUI との共通化基盤を整備。
  ゆり橋 12 本を per-cable + tension 初期条件で検証（Excel FEM 参照値と
  最大 RMS 0.56% で一致）。
- **2026-04-12**: `MooringLine` → `LumpedCable` にリネーム（旧名は
  `using` エイリアスで後方互換維持）。`LumpedCableSystem` + `CableAttachment`
  + `CableProperties` を導入し、cable_solver と BEM 時間ループの両方を
  System ベースに移行。多重ライン入力 / 出力スキーマ追加。pycable GUI に
  Lines list と Run-full-system を追加。

## TODO

### ソルバ機能拡張

- [x] **動的モード (`mode: "dynamic"`) の実装**。sinusoidal prescribed motion に対応（2026-04-13）。
- [ ] **動的境界条件の拡張**。時系列入力（CSV）、モーダル変形、mesh body への接続。
- [ ] **空気モードの切替**。`getDragForce()` の `_WATER_DENSITY_` ハードコードを
  引数化し、流体種別（水／空気）を JSON で指定可能にする。
- [ ] **風速場の注入**。最小実装は一様風、発展形は高度プロファイル、
  Davenport/von Kármán スペクトル、ガスト入力。
- [ ] **準定常空力モデル**。独立性原理で $C_D(\alpha), C_L(\alpha)$ を
  断面形状ごとに差し替え可能にする。ギャロッピングの Den Hartog 条件
  $(\partial C_L/\partial\alpha)|_{\alpha_0} + C_D(\alpha_0) < 0$ を判定する
  診断出力も欲しい。検討メモは [memo.md](memo.md) L205–L266 参照。
- [ ] **曲げ剛性 $EI$ と回転拘束**。`CableProperties::EI` フィールドは
  追加済みだが未使用。純 string モデルから 3 点離散曲げ（または
  co-rotational beam）への拡張。
- [ ] **Rayleigh 構造減衰**。既存の `networkLine::damping` は隣接節点間粘性
  なので、別途節点絶対速度に対する質量比例項 $\alpha \mathbf{M}$ を加える。
- [x] **プリテンション指定モード**。`initial_condition: "tension"` + `tension_top` / `tension_bottom` で secant method 反復（2026-04-13）。

### 橋梁ケーブル検証 (`examples/yuri_bridge/`)

- [ ] C01–C12 をまとめて回すバッチスクリプトと、Excel の軸力参照値との比較
  レポート生成（`yuri_bridge_all.json` + 多重ラインモードで既に 1 コマンド
  実行可）。
- [ ] 温度荷重ケース（7 種）への対応。
- [ ] `line_density` の単位「kg/m」と線素密度 $\rho A$ の整合ドキュメント。

### 整理

- [ ] 旧バイナリ (`main`, `example_using_Network`, `example_validation1`) と
  未使用 `.cpp` サンプルを `legacy/` へ退避 or 削除。
- [ ] 古い leapfrog 結果 JSON と `sample*.gif` の整理。
- [ ] `weight_per_unit_length` メンバ名を `mass_per_length` に統一（今は
  引数名だけ統一済み）。

### 公開リポ反映

- [ ] `examples/yuri_bridge/` の公開可否判断。現状は dev only。
- [ ] [memo.md](memo.md) の橋梁風応答セクションを、dev 内検討に留めるか、
  英訳して公開するか決める。

---

License: LGPL-3.0-or-later（BEM 本体と同じ）。
