#!/bin/bash -xe

#brew install coreutils

# Model name.
model_name="C8"
dag_builder="C8a"
if [[ 0 == 1 ]]; then
    # Dev2.
    source_dir="/data/saggese/src_vc/lemonade1"
    target_dir="/data/saggese/src/orange1"
else
    # Mac.
    source_dir="/Users/saggese/src/lemonade1"
    target_dir="/Users/saggese/src/orange1"
fi;

# Install pyarmor.
#sudo /bin/bash -c "(source /venv/bin/activate; pip install pyarmor)"
pip install pyarmor

# 1) Encrypt module.
pyarmor obfuscate --restrict=0 --recursive dataflow_lemonade/pipelines/${model_name} --output dataflow_lemonade/pipelines/${model_name}_encr
# Add the import.
filename=dataflow_lemonade/pipelines/${model_name}_encr/__init__.py
(echo "from .pytransform import pyarmor_runtime; pyarmor_runtime()" >tmp; cat $filename >>tmp); mv tmp $filename

cp -r ${source_dir}/dataflow_lemonade/pipelines/${model_name}_encr ${target_dir}/dataflow_orange/pipelines/$model_name

# 2) Encrypt libraries.

#> find core_lem -name "*.py" | grep -v notebooks
#core_lem/dataflow/nodes/__init__.py
#core_lem/dataflow/__init__.py
#core_lem/__init__.py
#core_lem/features.py
filenames="core_lem/__init__.py core_lem/features.py"
dst_dir="core_lem"
if [[ -d ${dst_dir}_tmp2 ]]; then
    rm -rf ${dst_dir}_tmp2
fi;
mkdir ${dst_dir}_tmp2
for filename in $filenames
do
    # --parents preserve subdir.
    # cp --parents $filename core_lem_tmp
    # rsync -R $filename core_lem_tmp
    # From https://stackoverflow.com/questions/11246070/cp-parents-option-on-mac
    gcp --parents $filename ${dst_dir}_tmp2/
done;
# The generated files are like:
# > find core_lem_tmp
# core_lem_tmp
# core_lem_tmp/core_lem
# core_lem_tmp/core_lem/__init__.py
# core_lem_tmp/core_lem/features.py
if [[ -d ${dst_dir}_tmp ]]; then
    rm -rf ${dst_dir}_tmp
fi;
mv ${dst_dir}_tmp2/* ${dst_dir}_tmp
rmdir ${dst_dir}_tmp2

# //////////

pyarmor obfuscate --restrict=0 --recursive ${dst_dir}_tmp --output ${dst_dir}_encr
file_name=${dst_dir}_encr/__init__.py
(echo "from .pytransform import pyarmor_runtime; pyarmor_runtime()" >tmp; cat $file_name >>tmp); mv tmp $file_name
cp -r ${source_dir}/${dst_dir}_encr ${target_dir}/${dst_dir}

filenames="dataflow_lemonade/pipelines/dag_builder_helpers.py"
dst_dir="dataflow_lemonade"
if [[ -d ${dst_dir}_tmp2 ]]; then
    rm -rf ${dst_dir}_tmp2
fi;
mkdir ${dst_dir}_tmp2
for filename in $filenames
do
    # From https://stackoverflow.com/questions/11246070/cp-parents-option-on-mac
    gcp --parents $filename ${dst_dir}_tmp2/
done;
if [[ -d ${dst_dir}_tmp ]]; then
    rm -rf ${dst_dir}_tmp
fi;
mv ${dst_dir}_tmp2/* ${dst_dir}_tmp
rmdir ${dst_dir}_tmp2

pyarmor obfuscate --restrict=0 --recursive ${dst_dir}_tmp --output ${dst_dir}_encr
file_name=${dst_dir}_encr/__init__.py
(echo "from .pytransform import pyarmor_runtime; pyarmor_runtime()" >tmp; cat $file_name >>tmp); mv tmp $file_name
cp -r ${source_dir}/${dst_dir}_encr ${target_dir}/${dst_dir}

# 3) Deploy model to target repo.
cat <<EOF >deploy_orange.sh
#!/bin/bash -xe
python -c 'import dataflow_orange.pipelines.$model_name.${dag_builder}_pipeline as f; a = f.${dag_builder}_DagBuilder(); print(a)'
EOF
chmod +x deploy_orange.sh
cp $source_dir/deploy_orange.sh $target_dir
(cd $target_dir; source dev_scripts_orange/setenv.sh; invoke docker_cmd --cmd "source ./deploy_orange.sh")
