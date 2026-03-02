from pathlib import Path
import random as rd
import shutil
import uuid
import webbrowser

from django.core.management.base import BaseCommand, CommandError

from ligand_service.tasks import _start_simulation
from ligand_service.models import get_trajectory_files, TrajectoryFiles

CLI_OUT_DIRECTORY = Path("cli").resolve()
USER_UPLOADS_DIR = Path("user_uploads").resolve()
USER_UPLOADS_DIR.mkdir(exist_ok=True)


class Command(BaseCommand):
    help = "Generates results from example simulations"

    def add_arguments(self, parser):
        parser.add_argument("input_sim", type=Path)
        parser.add_argument("--create-page", action="store_true")
        parser.add_argument("--frames", type=int)

    def handle(self, *args, **options):
        input_sim = options["input_sim"]
        frame_count = options["frames"]
        # added so no collisions happen
        path_salt = "".join([str(rd.randint(0, 9)) for _ in range(6)])
        sim_dir = CLI_OUT_DIRECTORY / str(input_sim.name + path_salt)

        print(f"Copying input sim to {sim_dir}")
        shutil.copytree(input_sim, sim_dir)

        files = get_trajectory_files(sim_dir)
        assert files is not None, "Simulation files not found"
        work_dir = sim_dir / "work"
        work_dir.mkdir(parents=True)
        res_dir = sim_dir / "results"
        res_dir.mkdir(parents=True)
        print("Starting analysis")
        _start_simulation(
            files.topology,
            files.trajectory,
            work_dir,
            res_dir,
            frame_count,
        )
        if options["create_page"]:
            random_uuid = str(uuid.uuid4())
            out_dir = USER_UPLOADS_DIR / random_uuid
            out_dir.mkdir(parents=True, exist_ok=True)
            for file in res_dir.iterdir():
                shutil.copy(file, out_dir)
            print("Files saved in: ", out_dir)
            webbrowser.open(f"http://localhost:8000/show/{random_uuid}")
