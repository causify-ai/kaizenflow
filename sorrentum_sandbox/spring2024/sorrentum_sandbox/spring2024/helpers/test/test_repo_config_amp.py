import logging

import pytest

import helpers.henv as henv
import helpers.hgit as hgit
import helpers.hserver as hserver
import helpers.hunit_test as hunitest
import helpers.hunit_test_utils as hunteuti
import helpers.repo_config_utils as hrecouti

_LOG = logging.getLogger(__name__)


# #############################################################################
# TestRepoConfig_Amp
# #############################################################################


class TestRepoConfig_Amp(hunitest.TestCase):
    # Difference between `cmamp` and `kaizenflow`.
    expected_repo_name = "//kaizen"

    def test_repo_name1(self) -> None:
        """
        Show that when importing repo_config, one doesn't get necessarily the
        outermost repo_config (e.g., for lime one gets amp.repo_config).
        """
        import repo_config

        actual = repo_config.get_name()
        _LOG.info(
            "actual=%s expected_repo_name=%s", actual, self.expected_repo_name
        )

    @pytest.mark.skipif(
        not hgit.is_in_amp_as_supermodule(),
        reason="Only run in amp as supermodule",
    )
    def test_repo_name2(self) -> None:
        """
        If //amp is a supermodule, then repo_config should report //amp.
        """
        actual = henv.execute_repo_config_code("get_name()")
        self.assertEqual(actual, self.expected_repo_name)

    @pytest.mark.skipif(
        not hgit.is_in_amp_as_submodule(), reason="Only run in amp as submodule"
    )
    def test_repo_name3(self) -> None:
        """
        If //amp is a supermodule, then repo_config should report something
        different than //amp.
        """
        actual = henv.execute_repo_config_code("get_name()")
        self.assertNotEqual(actual, self.expected_repo_name)

    def test_config_func_to_str(self) -> None:
        _LOG.info(henv.execute_repo_config_code("config_func_to_str()"))

    def test_is_dev4(self) -> None:
        """
        Amp could run on dev4 or not.
        """
        _ = hserver.is_dev4()

    def test_is_CK_S3_available(self) -> None:
        """
        When running Amp on dev_ck, the CK bucket should be available.
        """
        if hserver.is_dev_ck():
            act = henv.execute_repo_config_code("is_CK_S3_available()")
            exp = True
            self.assertEqual(act, exp)


# #############################################################################
# TestRepoConfig_Amp_signature
# #############################################################################


# > pytest ./amp/helpers/test/test_repo_config_amp.py


class TestRepoConfig_Amp_signature1(hunitest.TestCase):
    def test_dev_ck_server(self) -> None:
        target_name = "amp"
        hunteuti.execute_only_in_target_repo(target_name)
        #
        hunteuti.execute_only_on_dev_ck()
        #
        exp = r"""
        # Repo config:
          # repo_config.config
            enable_privileged_mode='True'
            get_docker_base_image_name='amp'
            get_docker_shared_group=''
            get_docker_user=''
            get_host_name='github.com'
            get_invalid_words='[]'
            get_shared_data_dirs='{'/data/shared': '/shared_data'}'
            has_dind_support='True'
            has_docker_sudo='True'
            is_CK_S3_available='True'
            run_docker_as_root='False'
            skip_submodules_test='False'
            use_docker_db_container_name_to_connect='False'
            use_docker_network_mode_host='False'
            use_docker_sibling_containers='False'
            # hserver.config
              is_AM_S3_available()='True'
              is_dev4()='False'
              is_dev_ck()='True'
              is_inside_ci()='False'
              is_inside_docker()='True'
              is_mac(version='Catalina')='False'
              is_mac(version='Monterey')='False'
              is_mac(version='Ventura')='False'
        # Env vars:
          AM_AWS_ACCESS_KEY_ID=undef
          AM_AWS_DEFAULT_REGION=undef
          AM_AWS_PROFILE='am'
          AM_AWS_S3_BUCKET='$AM_AWS_S3_BUCKET'
          AM_AWS_SECRET_ACCESS_KEY=undef
          AM_ECR_BASE_PATH='$AM_ECR_BASE_PATH'
          AM_ENABLE_DIND='1'
          AM_FORCE_TEST_FAIL=''
          AM_REPO_CONFIG_CHECK='True'
          AM_REPO_CONFIG_PATH=''
          AM_TELEGRAM_TOKEN=***
          CI=''
          GH_ACTION_ACCESS_TOKEN=empty
          """
        hunteuti.check_env_to_str(self, exp)

    def test_mac(self) -> None:
        target_name = "amp"
        hunteuti.execute_only_in_target_repo(target_name)
        #
        hunteuti.execute_only_on_mac(version="Catalina")
        #
        exp = r"""
        # Repo config:
            # repo_config.config
            enable_privileged_mode='False'
            get_docker_base_image_name='amp'
            get_docker_shared_group=''
            get_docker_user=''
            get_host_name='github.com'
            get_invalid_words='[]'
            get_shared_data_dirs='None'
            has_dind_support='False'
            has_docker_sudo='True'
            is_CK_S3_available='False'
            run_docker_as_root='False'
            skip_submodules_test='False'
            use_docker_db_container_name_to_connect='True'
            use_docker_network_mode_host='False'
            use_docker_sibling_containers='True'
            # hserver.config
              is_AM_S3_available='True'
              is_dev4='False'
              is_dev_ck='False'
              is_inside_ci='False'
              is_inside_docker='True'
              is_mac='True'
        # Env vars:
        AM_AWS_ACCESS_KEY_ID=undef
        AM_AWS_DEFAULT_REGION=undef
        AM_AWS_PROFILE='am'
        AM_AWS_S3_BUCKET='alphamatic-data'
        AM_AWS_SECRET_ACCESS_KEY=undef
        AM_ECR_BASE_PATH='665840871993.dkr.ecr.us-east-1.amazonaws.com'
        AM_ENABLE_DIND='1'
        AM_FORCE_TEST_FAIL=''
        AM_REPO_CONFIG_CHECK='False'
        AM_REPO_CONFIG_PATH=''
        AM_TELEGRAM_TOKEN=***
        CI=''
        GH_ACTION_ACCESS_TOKEN=empty
        """
        hunteuti.check_env_to_str(self, exp)
        #
        exp_enable_privileged_mode = True
        exp_has_dind_support = True
        hrecouti.assert_setup(
            self, exp_enable_privileged_mode, exp_has_dind_support
        )

    @pytest.mark.skipif(
        not henv.execute_repo_config_code("get_name()") == "//amp",
        reason="Run only in //amp",
    )
    def test_amp_ci(self) -> None:
        hunteuti.execute_only_on_ci()
        #
        exp = r"""
        # Repo config:
          # repo_config.config
            enable_privileged_mode='True'
            get_docker_base_image_name='amp'
            get_docker_shared_group=''
            get_docker_user=''
            get_host_name='github.com'
            get_invalid_words='[]'
            get_shared_data_dirs='None'
            has_dind_support='True'
            has_docker_sudo='False'
            is_CK_S3_available='False'
            run_docker_as_root='True'
            skip_submodules_test='False'
            use_docker_db_container_name_to_connect='False'
            use_docker_network_mode_host='False'
            use_docker_sibling_containers='False'
            # hserver.config
              is_AM_S3_available()='True'
              is_dev4()='False'
              is_dev_ck()='False'
              is_inside_ci()='True'
              is_inside_docker()='True'
              is_mac(version='Catalina')='False'
              is_mac(version='Monterey')='False'
              is_mac(version='Ventura')='False'
        # Env vars:
          AM_ECR_BASE_PATH='$AM_ECR_BASE_PATH'
          AM_ENABLE_DIND='1'
          AM_FORCE_TEST_FAIL=''
          AM_REPO_CONFIG_CHECK='True'
          AM_REPO_CONFIG_PATH=''
          CI='true'
        """
        # We ignore the AWS vars, since GH Actions does some replacement to mask
        # the env vars coming from secrets.
        skip_secrets_vars = True
        hunteuti.check_env_to_str(self, exp, skip_secrets_vars=skip_secrets_vars)

    @pytest.mark.skipif(
        not henv.execute_repo_config_code("get_name()") == "//cmamp",
        reason="Run only in //cmamp",
    )
    def test_cmamp_ci(self) -> None:
        hunteuti.execute_only_on_ci()
        #
        exp = r"""
        # Repo config:
          # repo_config.config
            enable_privileged_mode='True'
            get_docker_base_image_name='cmamp'
            get_docker_shared_group=''
            get_docker_user=''
            get_host_name='github.com'
            get_html_dir_to_url_mapping='{'s3://cryptokaizen-html': 'http://172.30.2.44'}'
            get_invalid_words='[]'
            get_shared_data_dirs='None'
            has_dind_support='True'
            has_docker_sudo='False'
            is_CK_S3_available='True'
            run_docker_as_root='True'
            skip_submodules_test='False'
            use_docker_db_container_name_to_connect='False'
            use_docker_network_mode_host='False'
            use_docker_sibling_containers='False'
            # hserver.config
              is_AM_S3_available()='True'
              is_dev4()='False'
              is_dev_ck()='False'
              is_inside_ci()='True'
              is_inside_docker()='True'
              is_mac(version='Catalina')='False'
              is_mac(version='Monterey')='False'
              is_mac(version='Ventura')='False'
        # Env vars:
          AM_ECR_BASE_PATH='$AM_ECR_BASE_PATH'
          AM_ENABLE_DIND='1'
          AM_FORCE_TEST_FAIL=''
          AM_REPO_CONFIG_CHECK='True'
          AM_REPO_CONFIG_PATH=''
          CI='true'
          CK_ECR_BASE_PATH='$CK_ECR_BASE_PATH'
        """
        # We ignore the AWS vars, since GH Actions does some replacement to mask
        # the env vars coming from secrets.
        skip_secrets_vars = True
        hunteuti.check_env_to_str(self, exp, skip_secrets_vars=skip_secrets_vars)
