#!/usr/bin/env python
"""
Encrypt and release a directory containing models

See docs/dataflow/ck.release_encrypted_models.explanation.md and
docs/dataflow/ck.release_encrypted_models.how_to_guide.md for details.

Usage:
# Encrypt models with the normal encryption flow.
> dev_scripts/encrypt_model.py \
    --input_dir dataflow_lemonade/pipelines \
    --model_dag_builder "C5a_DagBuilder" \
    --model_dag_builder_file "C5/C5a_pipeline.py" \
    -v DEBUG

# Encrypt models with cross-compile options.
> dev_scripts/encrypt_model.py \
    --input_dir dataflow_lemonade/pipelines \
    --build_target "linux/amd64" \
    --model_dag_builder "C5a_DagBuilder" \
    --model_dag_builder_file "C5/C5a_pipeline.py \
    -v DEBUG
"""
import argparse
import logging
import os
import pathlib
import re

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hparser as hparser
import helpers.hprint as hprint
import helpers.hserver as hserver
import helpers.hsystem as hsystem

_LOG = logging.getLogger(__name__)


def _encrypt_input_dir(
    input_dir: str,
    output_dir: str,
    docker_build_target: str,
    docker_image_tag: str,
) -> str:
    """
    Encrypt a dir storing models using Pyarmor.

    :param input_dir: source model directory
    :param output_dir: encrypted model output directory
    :param build_target: Docker cross-building option (e.g. `linux/amd64`)
    :param docker_image_tag: Docker image tag
    """
    hdbg.dassert_type_is(docker_image_tag, str)
    # Create encrypted model directory.
    hio.create_dir(output_dir, incremental=False)
    # Get user and group id.
    user_id_cmd = "id -u"
    _, user_id = hsystem.system_to_string(user_id_cmd)
    group_id_cmd = "id -g"
    _, group_id = hsystem.system_to_string(group_id_cmd)
    # Check the expected Python version.
    # TODO(gp): Add a switch to skip, since it is a slow check.
    exp_python_version = "3.9.5"
    if False:
        act_python_version = _get_python_version_in_docker()
        # Python version in docker should be same as Python version used to encrypt.
        hdbg.dassert_eq(act_python_version, exp_python_version)
    # Create temporary Dockerfile.
    # TODO(gp): Potentially we could install pyarmor on top of the Dev
    #  container to guarantee that the generated code is compatible with the
    #  Python inside the Dev container. For now we just enforce the version of
    #  Python to be the same as the Dev container.
    temp_dockerfile_path = "./tmp.encrypt_model.Dockerfile"
    with open(temp_dockerfile_path, "w") as temp_dockerfile:
        if hserver.is_mac():
            temp_dockerfile.write(
                f"""
                    FROM python:{exp_python_version}
                    RUN groupmod -n mygroup utmp
                    RUN useradd -u {user_id} -g mygroup myuser
                    RUN pip install pyarmor
                    RUN mkdir -p /home/myuser && chown myuser:mygroup /home/myuser
                    USER myuser
                """
            )
        else:
            temp_dockerfile.write(
                f"""
                    FROM python:{exp_python_version}
                    RUN groupadd -g {group_id} mygroup && useradd -u {user_id} -g mygroup myuser
                    RUN pip install pyarmor
                    RUN mkdir -p /home/myuser && chown myuser:mygroup /home/myuser
                    USER myuser
                """
            )
    # Build Docker image.
    _LOG.info("Building Docker image from %s", temp_dockerfile_path)
    if docker_build_target is not None:
        cmd = f"docker buildx build --platform {docker_build_target} -f {temp_dockerfile_path} -t {docker_image_tag} --build-arg user_id={user_id} --build-arg group_id={group_id} ."
    else:
        cmd = f"docker build -f {temp_dockerfile.name} -t {docker_image_tag} --build-arg user_id={user_id} --build-arg group_id={group_id} ."
    (_, output) = hsystem.system_to_string(cmd)
    _LOG.debug(output)
    #os.remove(temp_dockerfile_path)
    # Run Docker container to encrypt the model.
    _LOG.info("Running Docker container.")
    work_dir = os.getcwd()
    docker_output_dir = "/app"
    mount = f"type=bind,source={work_dir},target={docker_output_dir}"
    encryption_flow = f"pyarmor-7 obfuscate --restrict=0 --recursive {input_dir} --output {output_dir}"
    if docker_build_target is not None:
        docker_cmd = f"docker run --rm -it --user {user_id}:{group_id} --platform {docker_build_target} --workdir {docker_output_dir} --mount {mount} {docker_image_tag} {encryption_flow}"
    else:
        docker_cmd = f"docker run --rm -it --user {user_id}:{group_id} --workdir {docker_output_dir} --mount {mount} {docker_image_tag} {encryption_flow}"
    (_, output) = hsystem.system_to_string(docker_cmd)
    _LOG.debug(output)
    # Check that command worked by ensuring that there are dirs in the target dir.
    n_files = len(os.listdir(output_dir))
    hdbg.dassert_lt(
        0, n_files, "No files in output_dir=`%s`", output_dir
    )
    _LOG.info(
        "Encrypted model successfully stored in output_dir='%s'",
        output_dir,
    )
    return output_dir

# TODO(gp): Add a function to check that everything is encrypted.
# find dataflow_lemonade/encrypted_pipelines -name "*.py" | grep -v pytransform | xargs -n 1 cat | grep -v "\x"


def _get_python_version_in_docker() -> str:
    """
    Get the Python version used in Docker.
    """
    cmd = f"invoke docker_cmd -c 'python -V'"
    _, output = hsystem.system_to_string(cmd)
    pattern = r"Python (\d+\.\d+\.\d+)"
    match = re.search(pattern, output)
    hdbg.dassert_is_not(match, None, f"Can't parse '{output}'")
    python_version = match.group(1)
    return python_version


def _tweak_init(encrypted_dir: str) -> None:
    """
    Add Pyarmor module to `__init__.py` to make sure that encrypted model works
    correctly.

    :param encrypted_dir: encrypted model directory (e.g.
        dataflow_amp/pipelines)
    """
    # Generate absolute path of `pytransform` import.
    encrypted_model_import_path = encrypted_dir.strip("/")
    encrypted_model_import_path = encrypted_model_import_path.replace("/", ".")
    pytransform_import_path = ".".join(
        [encrypted_model_import_path, "pytransform"]
    )
    pytransform_import = f"from {pytransform_import_path} import pyarmor_runtime; pyarmor_runtime()"
    # Find all `__init__.py` under encrypted model directory except for the one
    # under `pytransform`.
    cmd = f'find {encrypted_dir} -name "__init__.py"'
    _, init_files = hsystem.system_to_string(cmd)
    files = init_files.split("\n")
    for f in files:
        file_path = pathlib.Path(f)
        if file_path.parent.name != "pytransform":
            data = hio.from_file(f)
            lines = "\n".join([pytransform_import, data])
            hio.to_file(f, lines)


def _test_model(model_dag_builder: str, model_dag_builder_file: str) -> None:
    """
    Check that a model works correctly.

    :param model_dag_builder: e.g., C5a_DagBuilder
    :param model_dag_builder_file: e.g.,
        dataflow_lemonade/pipelines/C5/C5a_pipeline.py
    """
    # _LOG.debug(hprint.to_str("input_dir model_dag_builder model_dag_builder_file"))
    # The expected Python command is:
    #   ```
    #   import dataflow_lemonade.pipelines.C5.C5a_pipeline as f;
    #   a = f.C5a_DagBuilder(); print(a)
    #   ```
    import_path = (
        pathlib.Path(model_dag_builder_file)
        .with_suffix("")
        .as_posix()
        .replace("/", ".")
    )
    script = f'python -c "import {import_path} as f; a = f.{model_dag_builder}(); print(a)"'
    # Write testing script to temporary file.
    temp_file_path = "./tmp.encrypt_model.test_model.sh"
    hio.to_file(temp_file_path, script)
    # Run test inside Docker container.
    cmd = f"invoke docker_cmd -c 'bash {temp_file_path}'"
    _, output = hsystem.system_to_string(cmd)
    _LOG.debug(output)
    #os.remove(temp_file_path)


def _test_models_in_dir(input_dir: str, model_dag_builder: str) -> None:
    """
    Test all models in a directory.
    """
    for model in os.scandir(input_dir):
        if model.is_dir() and model.name != "pytransform":
            _LOG.info("Testing model %s.", model.name)
            _test_model(model.path, model_dag_builder)


# #############################################################################


def _parse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--input_dir", required=True, type=str, help="Source model directory"
    )
    parser.add_argument(
        "--build_target",
        default=None,
        choices=["linux/arm64", "linux/amd64", "linux/amd64,linux/arm64"],
        type=str,
        help="Specify cross-build options for Docker container",
    )
    parser.add_argument(
        "--output_dir",
        required=False,
        default=None,
        type=str,
        help="Encrypted model output directory",
    )
    parser.add_argument(
        "--release_dir",
        required=False,
        default=None,
        type=str,
        help="Encrypted model release directory",
    )
    parser.add_argument(
        "--docker_image_tag",
        required=False,
        default="encryption_flow",
        type=str,
        help="Docker image tag",
    )
    # Testing model.
    parser.add_argument(
        "--test", default=False, action="store_true", help="Run testing"
    )
    parser.add_argument(
        "--model_dag_builder",
        required=False,
        type=str,
        help="Model DAG builder name",
    )
    parser.add_argument(
        "--model_dag_builder_file",
        required=False,
        type=str,
        help="Path to the file storing the model DAG builder",
    )
    hparser.add_verbosity_arg(parser)
    return parser


# TODO(gp): Split this code in function, one per function.
def _main(parser: argparse.ArgumentParser) -> None:
    hdbg.dassert(not hserver.is_inside_docker(),
            "This script runs outside the dev container and in the thin environment")
    args = parser.parse_args()
    hdbg.init_logger(verbosity=args.log_level, use_exec_path=True)
    #
    input_dir = args.input_dir
    hdbg.dassert_dir_exists(input_dir)
    _LOG.info("input_dir=%s", input_dir)
    output_dir = args.output_dir
    # If `output_dir` is not specified, use the parent directory of `input_dir`.
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(input_dir),
            "encrypted_" + os.path.basename(input_dir))
    _LOG.info("output_dir=%s", output_dir)
    # Get the DAG builder.
    if args.test:
        hdbg.dassert_is_not(args.model_dag_builder, None)
    if args.model_dag_builder is not None:
        hdbg.dassert_is_not(args.model_dag_builder_file, None)
        model_file = os.path.join(input_dir, args.model_dag_builder_file)
        _LOG.info("model_file=%s", model_file)
        hdbg.dassert_file_exists(model_file)
    # 1) Test original model.
    if args.test:
        _LOG.info("\n" + hprint.frame("1) Test original model"))
        model_dag_builder_file_org = os.path.join(
            input_dir, args.model_dag_builder_file
        )
        _test_model(args.model_dag_builder, model_dag_builder_file_org)
    # 2) Encrypt the dir.
    _LOG.info("\n" + hprint.frame("2) Encrypt the dir"))
    # E.g., output_dir looks like `dataflow_lemonade/encrypted_pipelines`.
    _encrypt_input_dir(
        input_dir, output_dir, args.build_target, args.docker_image_tag
    )
    # 3) Tweak `__init__.py` file.
    _LOG.info("\n" + hprint.frame("3) Fix init files"))
    _tweak_init(output_dir)
    # 4) Test encrypted model.
    if args.test:
        _LOG.info("\n" + hprint.frame("4) Test encrypted model"))
        model_dag_builder_file_enc = os.path.join(
            output_dir, args.model_dag_builder_file
        )
        _test_model(args.model_dag_builder, model_dag_builder_file_enc)
    # 5) Release encrypted model.
    if args.release_dir:
        _LOG.info("\n" + hprint.frame("5) Release encrypted model"))
        # Copy the encrypted files to the release dir and add them to Git,
        # removing the old files.
        hio.create_dir(args.release_dir, incremental=True)
        # - Extract the git root in the release folder.
        _, release_git_root = hsystem.system_to_string(
            f"cd {args.release_dir}; git rev-parse --show-toplevel"
        )
        # - Remove the old files from Git.
        # E.g., cd /data/saggese/src/orange1; git rm -rf --ignore-unmatch dataflow_lemonade/encrypted_pipeline
        release_base_dir = os.path.relpath(args.release_dir, release_git_root)
        _, output = hsystem.system_to_string(
            f"cd {release_git_root}; git rm -rf --ignore-unmatch {release_base_dir}"
        )
        # - Copy the encrypted dir in the target dir.
        # E.g., cp -r /data/saggese/src_vc/lemonade1/dataflow_lemonade/encrypted_pipelines /data/saggese/src/orange1/dataflow_lemonade/encrypted_pipeline
        input_dir_tmp = os.path.abspath(output_dir)
        # We need to move the encrypted code in the same place as the original
        # code in the release tree.
        output_dir_tmp = os.path.abspath(args.release_dir)
        _, output = hsystem.system_to_string(f"cp -r {input_dir_tmp} {output_dir_tmp}")
        # ls /data/saggese/src_vc/lemonade1/dataflow_lemonade/encrypted_pipelines
        cmd = f"ls {input_dir_tmp}"
        hsystem.system(cmd, suppress_output=False)
        # ls /data/saggese/src/orange1/dataflow_lemonade/encrypted_pipeline/
        cmd = f"ls {output_dir_tmp}"
        hsystem.system(cmd, suppress_output=False)
        # - Add the encrypted files back to Git.
        # E.g., cd /data/saggese/src/orange1; git add dataflow_lemonade/encrypted_pipeline
        _, output = hsystem.system_to_string(
            f"cd {release_git_root}; git add {release_base_dir}"
        )
        cmd = f"ls {output_dir_tmp} | xargs"
        hsystem.system(cmd, suppress_output=False)
        # - Change the paths.
        # E.g., from dataflow_lemonade.encrypted_pipelines.pytransform import pyarmor_runtime; pyarmor_runtime()
        # TODO(gp): Remove the overfit to the dir name and the old/new names.
        cmd = f'replace_text.py --only_dirs {release_git_root}/dataflow_lemonade --old "encrypted_pipelines" --new "pipelines"'
        hsystem.system(cmd)
        # TODO(gp): Test in the release dir
        # python -c "import dataflow_lemonade.pipelines.C11.C11a_pipeline as f; a = f.C11a_DagBuilder(); print(a)"


if __name__ == "__main__":
    _main(_parse())
