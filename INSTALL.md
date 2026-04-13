# インストール手順

プラットフォーム別のダウンロードからテスト実行までの手順．

## Mac

前提: Xcode Command Line Tools，Homebrew が入っていること．

```bash
# 1. 依存パッケージ
xcode-select --install          # 初回のみ
brew install gcc cmake lapack

# 2. リポジトリ取得
git clone https://github.com/tomoakihirakawa/CableDynamics.git
cd CableDynamics

# 3. ソルバビルド
mkdir -p cable/build_solver && cd cable/build_solver
cmake -DCMAKE_BUILD_TYPE=Release -DSOURCE_FILE=cable/cable_solver.cpp ../..
make -j$(sysctl -n hw.logicalcpu)
cd ../..

# 4. テスト実行（単体ケーブル）
cable/build_solver/cable_solver cable/gui/examples/catenary_500m.json /tmp/cable_test
cat /tmp/cable_test/result.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'top_tension={d[\"top_tension\"]:.2f} N  converged={d[\"converged\"]}')"

# 5. GUI 起動（Python 3.9–3.12 推奨）
cd cable/gui
./run.sh   # 初回は venv 作成 + pip install が走る
```

## Linux（Ubuntu 22.04+ / Debian 12+）

```bash
# 1. 依存パッケージ
sudo apt update
sudo apt install -y g++ cmake liblapack-dev libblas-dev git python3 python3-venv python3-pip

# 2. リポジトリ取得
git clone https://github.com/tomoakihirakawa/CableDynamics.git
cd CableDynamics

# 3. ソルバビルド
mkdir -p cable/build_solver && cd cable/build_solver
cmake -DCMAKE_BUILD_TYPE=Release -DSOURCE_FILE=cable/cable_solver.cpp ../..
make -j$(nproc)
cd ../..

# 4. テスト実行
cable/build_solver/cable_solver cable/gui/examples/catenary_500m.json /tmp/cable_test
cat /tmp/cable_test/result.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'top_tension={d[\"top_tension\"]:.2f} N  converged={d[\"converged\"]}')"

# 5. GUI 起動
cd cable/gui
./run.sh
```

> **Note**: GUI には X11 または Wayland のディスプレイサーバが必要．
> WSL2 の場合は `export DISPLAY=:0` または WSLg（Windows 11）を利用．
>
> Linux での動作は未検証．問題がある場合は，エラーメッセージを添えてご連絡ください．

## Windows（MSYS2 / MinGW-w64）

```powershell
# 1. MSYS2 をインストール（https://www.msys2.org/）
# MSYS2 MINGW64 ターミナルを開いて以下を実行:

pacman -Syu
pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-lapack mingw-w64-x86_64-openblas git

# 2. リポジトリ取得
git clone https://github.com/tomoakihirakawa/CableDynamics.git
cd CableDynamics

# 3. ソルバビルド
mkdir -p cable/build_solver && cd cable/build_solver
cmake -G "MSYS Makefiles" -DCMAKE_BUILD_TYPE=Release -DSOURCE_FILE=cable/cable_solver.cpp ../..
make -j$(nproc)
cd ../..

# 4. テスト実行
cable/build_solver/cable_solver.exe cable/gui/examples/catenary_500m.json /tmp/cable_test

# 5. GUI（Python 3.9–3.12 を別途インストール）
cd cable/gui
python -m venv .venv
.venv/Scripts/activate
pip install -e .
python -m pycable
```

> **Note**: Windows ネイティブ（Visual Studio）でのビルドは GNU 拡張 (`-std=gnu++23`) の非互換により非推奨．
> MSYS2/MinGW-w64 経由で GCC を使うことを推奨．
>
> Windows での動作は未検証．問題がある場合は，エラーメッセージを添えてご連絡ください．
