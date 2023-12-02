#!/bin/bash
venv_name="my_venv"
python3 -m venv $venv_name
source $venv_name/bin/activate
pip install -r requirements.txt
echo "Virtual environment $venv_name created and activated."

