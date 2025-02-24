The most updated example of how to create Docker containers is 
- `//sorrentum/sorrentum_sandbox/docker_common`
- `//sorrentum/sorrentum_sandbox/devops`

# Some common operations:

- Find all the directory with lightweight Docker flow
  ```
  > find . -name "docker_bash.sh"
  ```

- Update the dev systems using the script
  //sorrentum/sorrentum_sandbox/docker_common/diff_repo.sh
  ```
  > DST_SUBDIR="umd_data605_1"
  > #DST_SUBDIR="umd_icorps"
  > #DST_SUBDIR="umd_defi"
   
  # Diff `docker_common` dir.
  > SRC_DIR=$HOME/src/sorrentum1/sorrentum_sandbox/docker_common; DST_DIR=$HOME/src/$DST_SUBDIR/docker_common; diff_to_vimdiff.py --dir1 $SRC_DIR --dir2 $DST_DIR
   
  # Diff `devops` dir.
  > SRC_DIR=$HOME/src/sorrentum1/sorrentum_sandbox/devops; DST_DIR=$HOME/src/$DST_SUBDIR/project/icorps; diff_to_vimdiff.py --dir1 $SRC_DIR --dir2 $DST_DIR

  # Diff `devops` dir.
  > SRC_DIR=$HOME/src/sorrentum1/defi/devops; DST_DIR=$HOME/src/$DST_SUBDIR/project/icorps; diff_to_vimdiff.py --dir1 $SRC_DIR --dir2 $DST_DIR
  ```
