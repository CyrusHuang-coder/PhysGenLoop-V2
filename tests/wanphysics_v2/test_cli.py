from argparse import Namespace
from pathlib import Path

from agents.wanphysics.run_videophy2_loop_v2 import build_arg_parser, _run_root


def test_active_cli_has_no_force_or_proxy_flags():
    parser = build_arg_parser()
    option_strings = {
        option
        for action in parser._actions
        for option in action.option_strings
    }
    assert "--force-action" not in option_strings
    assert "--allow-proxy-policy" not in option_strings
    assert "--retry-failed" in option_strings


def test_explicit_output_root_is_final_directory(tmp_path):
    args = Namespace(output_root=str(tmp_path / "run"))
    assert _run_root(args) == (tmp_path / "run").resolve()
