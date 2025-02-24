#!/bin/bash -xe
#> ls -1 amp/helpers/
#README.md

#AMP_DIR=/Users/saggese/src/lemonade2/amp
#SUPER_DIR=/Users/saggese/src/lemonade2

#AMP_DIR=/Users/saggese/src/dev_tools1/amp
#SUPER_DIR=/Users/saggese/src/dev_tools1

AMP_DIR=/Users/saggese/src/cmamp1

#(cd $SUPER_DIR; git reset --hard)
(cd $AMP_DIR; git reset --hard)

#replace_text="dev_scripts/replace_text.py --dst_dir $SUPER_DIR "
replace_text="dev_scripts/replace_text.py --dst_dir $AMP_DIR "

#__init__.py
#build_helpers_package.sh
#cache.md
#cache.py
(cd $AMP_DIR; git mv helpers/cache.py helpers/hcache.py; git mv helpers/cache.md helpers/hcache.md)
$replace_text --old 'import helpers.cache' --new 'import helpers.hcache'

#dataframe.py

(cd $AMP_DIR; git mv helpers/dataframe.py helpers/hdataframe.py)
$replace_text --old 'import helpers.dataframe' --new 'import helpers.hdataframe'

#datetime_.py

(cd $AMP_DIR; git mv helpers/datetime_.py helpers/hdatetime.py)
$replace_text --old 'import helpers.datetime_' --new 'import helpers.hdatetime'

#dbg.py

(cd $AMP_DIR; git mv helpers/dbg.py helpers/hdbg.py)
$replace_text --old 'import helpers.dbg' --new 'import helpers.hdbg'

#dict.py
(cd $AMP_DIR; git mv helpers/dict.py helpers/hdict.py)
$replace_text --old 'import helpers.dict' --new 'import helpers.hdict'

#docker_manager.py
(cd $AMP_DIR; git mv helpers/docker_manager.py helpers/hdocker.py)
$replace_text --old 'import helpers.docker_manager' --new 'import helpers.hdocker_manager'

#env.py
(cd $AMP_DIR; git mv helpers/env.py helpers/henv.py)
$replace_text --old 'import helpers.env' --new 'import helpers.henv'

#git.py
(cd $AMP_DIR;git mv helpers/git.py helpers/hgit.py)
$replace_text --old 'import helpers.git' --new 'import helpers.hgit'

#hasyncio.py
#hcsv.py

#hnumpy.py
#hpandas.py
#hparquet.py
#hsql_test.py
#htqdm.py
#htypes.py

#introspection.py
(cd $AMP_DIR;git mv helpers/introspection.py helpers/hintrospection.py)
$replace_text --old 'import helpers.introspection' --new 'import helpers.hintrospection'

#io_.py
(cd $AMP_DIR;git mv helpers/io_.py helpers/hio.py)
$replace_text --old 'import helpers.io_' --new 'import helpers.hio'

#joblib_helpers.md
#joblib_helpers.py
(cd $AMP_DIR;git mv helpers/joblib_helpers.py helpers/hjoblib.py; git mv helpers/joblib_helpers.md helpers/hjoblib.md)
$replace_text --old 'import helpers.joblib_helpers' --new 'import helpers.hjoblib'

#jupyter.py
(cd $AMP_DIR;git mv helpers/jupyter.py helpers/hjupyter.py)
$replace_text --old 'import helpers.jupyter' --new 'import helpers.hjupyter'

#lib_tasks.py
#list.py
(cd $AMP_DIR;git mv helpers/list.py helpers/hlist.py)
$replace_text --old 'import helpers.list' --new 'import helpers.hlist'

#network.py
(cd $AMP_DIR;git mv helpers/network.py helpers/hnetwork.py)
$replace_text --old 'import helpers.network' --new 'import helpers.hnetwork'

#notebooks

#numba_.py
(cd $AMP_DIR;git mv helpers/numba_.py helpers/hnumba.py)
$replace_text --old 'import helpers.numba_' --new 'import helpers.hnumba'
#old

#open.py
(cd $AMP_DIR;git mv helpers/open.py helpers/hopen.py)
$replace_text --old 'import helpers.open' --new 'import helpers.hopen'

#parser.py
(cd $AMP_DIR;git mv helpers/parser.py helpers/hparser.py)
$replace_text --old 'import helpers.parser' --new 'import helpers.hparser'

#pickle_.py
(cd $AMP_DIR;git mv helpers/pickle_.py helpers/hpickle.py)
$replace_text --old 'import helpers.pickle_' --new 'import helpers.hpickle'

#playback.md
#playback.py
(cd $AMP_DIR;git mv helpers/playback.py helpers/hplayback.py; git mv helpers/playback.md helpers/hplayback.md)
$replace_text --old 'import helpers.playback' --new 'import helpers.hplayback'

#printing.py
(cd $AMP_DIR;git mv helpers/printing.py helpers/hprint.py)
$replace_text --old 'import helpers.printing' --new 'import helpers.hprint'

#pytest_.py
(cd $AMP_DIR;git mv helpers/pytest_.py helpers/hpytest.py)
$replace_text --old 'import helpers.pytest_' --new 'import helpers.hpytest'

#s3.py
(cd $AMP_DIR;git mv helpers/s3.py helpers/hs3.py)
$replace_text --old 'import helpers.s3' --new 'import helpers.hs3'

#send_email.py
(cd $AMP_DIR;git mv helpers/send_email.py helpers/hemail.py)
$replace_text --old 'import helpers.send_email' --new 'import helpers.hemail'

#sql.py
(cd $AMP_DIR;git mv helpers/sql.py helpers/hsql.py)
$replace_text --old 'import helpers.sql' --new 'import helpers.hsql'

#system_interaction.py
(cd $AMP_DIR;git mv helpers/system_interaction.py helpers/hsystem.py)
$replace_text --old 'import helpers.system_interaction' --new 'import helpers.hsystem'

#table.py
(cd $AMP_DIR;git mv helpers/table.py helpers/htable.py)
$replace_text --old 'import helpers.table' --new 'import helpers.htable'

#telegram_notify

#test

#timer.py
(cd $AMP_DIR;git mv helpers/timer.py helpers/htimer.py)
$replace_text --old 'import helpers.timer' --new 'import helpers.htimer'

#traceback_helper.py
(cd $AMP_DIR;git mv helpers/traceback_helper.py helpers/htraceback.py)
$replace_text --old 'import helpers.traceback_helper' --new 'import helpers.htraceback'

#translate.py
(cd $AMP_DIR;git mv helpers/translate.py helpers/htranslate.py)
$replace_text --old 'import helpers.translate' --new 'import helpers.htranslate'

#unit_test.py
(cd $AMP_DIR;git mv helpers/unit_test.py helpers/hunit_test.py)
$replace_text --old 'import helpers.unit_test' --new 'import helpers.hunit_test'

#unit_test_skeleton.py

#versioning.py
(cd $AMP_DIR;git mv helpers/versioning.py helpers/hversion.py)
$replace_text --old 'import helpers.versioning' --new 'import helpers.hversion'

#warnings_helpers.py
(cd $AMP_DIR;git mv helpers/warnings_helpers.py helpers/hwarnings.py)
$replace_text --old 'import helpers.warnings_helpers' --new 'import helpers.hwarnings'
