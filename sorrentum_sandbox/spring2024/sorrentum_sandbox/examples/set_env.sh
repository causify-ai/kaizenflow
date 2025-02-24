set -o vi
#jupyter nbextension enable vim_binding/vim_binding
cd /data
export PYTHONPATH=$PYTHONPATH:/data
echo "PYTHONPATH=$PYTHONPATH"
python3 -c "import helpers.hdbg; print(helpers.hdbg)"
