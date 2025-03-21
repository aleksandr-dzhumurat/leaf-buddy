# leaf-buddy
AI-budtender



```shell
make prepare-dirs && \
pyenv install 3.11 && \
pyenv virtualenv 3.11 leafbuddy-env || true && \
source ~/.pyenv/versions/leafbuddy-env/bin/activate &&
pip install --upgrade pip && \
pip install -r requirements.txt
```

Run jupyter
```shell
make run-jupyter-env
```

# Data preparation

go to [search page](https://www.allbud.com/marijuana-strains/search?results=10) reluslts ad reload pge with `results=5000` param. Wait a minute or two while results is loading.

Save result as HTML and move html to `cp ~/Downloads/allbud.html ./data/pipelines-data`

Run preparation script

```shell
ROOT_DATA_DIR=$(pwd)/data/pipelines-data python services/etl/src/prepare_data.py
```

# Test dialog locally

Run dialog
```shell
make run-dialog
```

# Deploy code
```ssh
rsync -avz /Users/username/PycharmProjects/leaf-buddy root@168.119.168.170:/root
```