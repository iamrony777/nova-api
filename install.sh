#!/usr/bin/bash

echo -e "Installing poetry using official installer"
curl -sSL https://install.python-poetry.org | python -

echo -e "Updating PATH"
echo 'export PATH=$HOME/.local/bin:$PATH' >> ~/.bashrc

exec $SHELL