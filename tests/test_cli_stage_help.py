import argparse
import ast
import contextlib
import importlib.util
import io
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_parser_factory():
    helper_path = ROOT / "funclip" / "utils" / "argparse_tools.py"
    spec = importlib.util.spec_from_file_location("cli_argparse_tools", helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    source_path = ROOT / "funclip" / "videoclipper.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    factory = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "get_parser"
    )
    namespace = {"argparse": argparse, "ArgumentParser": helper.ArgumentParser}
    # Exercise the real parser without importing model and video dependencies.
    exec(compile(ast.Module(body=[factory], type_ignores=[]), str(source_path), "exec"), namespace)
    return namespace["get_parser"]


class CLIStageHelpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.make_parser = staticmethod(load_parser_factory())

    def test_help_describes_recognition_and_clipping_stages(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as result:
            self.make_parser().parse_args(["--help"])
        self.assertEqual(result.exception.code, 0)
        help_text = " ".join(output.getvalue().split())
        self.assertIn("1 for recognizing and 2 for clipping", help_text)
        self.assertNotIn("0 for recognizing", help_text)

    def test_stage_one_and_two_remain_accepted(self):
        for stage in (1, 2):
            with self.subTest(stage=stage):
                args = self.make_parser().parse_args(
                    ["--stage", str(stage), "--file", "example.mp4"]
                )
                self.assertEqual(args.stage, stage)

    def test_stage_zero_remains_invalid(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
            self.make_parser().parse_args(["--stage", "0", "--file", "example.mp4"])
        self.assertEqual(result.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
