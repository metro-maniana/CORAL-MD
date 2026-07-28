from datetime import datetime, timedelta
from pathlib import Path
import json
import logging
import functools
import shutil
import pandas as pd

from huey import crontab
from huey.contrib.djhuey import periodic_task, task
import polars as pl

from django.conf import settings

from ligand_service.models import Simulation

from .contacts import (
    get_trajectory_frame_count,
    create_translation_dict_by_blast,
    get_interactions_from_trajectory,
)

from .graphs import (
    plot_contact_fraction_heatmap,
    plot_correlation_covariance_heatmaps,
    create_getcontacts_table,
    create_interaction_area_graph,
    create_time_resolved_map,
)

from .handle_plip import extract_plip_report

LIGAND_DETECTION_THRESHOLD = 0.7
INCHIKEY_TO_NAME_JSON_PATH = Path("./chebi/inchikey_to_name.json")
INCHIKEY_TO_CHEBIID_JSON_PATH = Path("./chebi/inchikey_to_chebiID.json")

INTERACTION_TYPE_RENAME = {
    "hydrophobic_interactions": "Hydrophobic",
    "hydrogen_bonds": "Hydrogen bond",
    "water_bridges": "Water bridge",
    "salt_bridges": "Salt bridge",
    "pi_stacks": "Pi-pi stacking",
    "pi_cation_interactions": "Pi-cation",
    "halogen_bonds": "Halogen bond",
    "metal_complexes": "Metal complex",
}

logger = logging.getLogger(__name__)


def log_exceptions(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Unhandled exception in {func.__name__}: {e}")
            raise

    return wrapper


def save_file(file_handle, path_to_save_location: Path):
    with open(path_to_save_location, "wb+") as destination:
        for chunk in file_handle.chunks():
            destination.write(chunk)


inchikey_to_name = {}
inchikey_to_chebiID = {}

if (
    not INCHIKEY_TO_CHEBIID_JSON_PATH.is_file()
    or not INCHIKEY_TO_NAME_JSON_PATH.is_file()
):
    print(
        "Files from ChEBI are not available, please run 'python manage.py getchebi' before starting the server."
    )
else:
    with open(INCHIKEY_TO_NAME_JSON_PATH) as f:
        inchikey_to_name = json.load(f)
    with open(INCHIKEY_TO_CHEBIID_JSON_PATH) as f:
        inchikey_to_chebiID = json.load(f)


def extract_frame_number(directory: Path):
    return int("".join([char for char in directory.name if char.isdigit()]))


def analyse_simulation(
    top_file: Path,
    traj_file: Path,
    lig_info: dict[str, tuple[str, str]],
    plip_dir: Path,
    results_dir: Path,
    frame_count: int | None = None,
):
    results_dir.mkdir(exist_ok=True, parents=True)

    run_data = {}
    plip_results_df = None
    report_dirs = [
        (extract_frame_number(dir), dir) for dir in plip_dir.iterdir() if dir.is_dir()
    ]
    for frame_number, dir in sorted(report_dirs):
        report = dir / "report.xml"
        frame_results_df = extract_plip_report(report)
        frame_results_df = frame_results_df.with_columns(
            pl.lit(frame_number).alias("frame")
        )
        if plip_results_df is not None:
            plip_results_df.extend(frame_results_df)
        else:
            plip_results_df = frame_results_df
    assert plip_results_df is not None
    plip_results_df = plip_results_df.lazy().filter(
        pl.col("lig_type") == "SMALLMOLECULE"
    )
    shutil.rmtree(plip_dir)
    blast_result = create_translation_dict_by_blast(top_file, traj_file)
    if blast_result is not None:
        dic, scores = blast_result
        plip_results_df = plip_results_df.with_columns(
            pl.concat_str(["res_chain", "res_name", "res_pos"], separator=":")
            .replace(dic, default=None)
            .alias("aligned_numbering")
        )

    smiles_dict = {lig: info[0] for lig, info in lig_info.items()}
    inchikey_dict = {lig: info[1] for lig, info in lig_info.items()}

    plip_results_df = plip_results_df.with_columns(
        pl.concat_str(["lig_name", "lig_pos"], separator="")
        .replace(smiles_dict)
        .alias("smiles"),
        pl.concat_str(["lig_name", "lig_pos"], separator="")
        .replace(inchikey_dict)
        .alias("inchikey"),
    )

    print("RESULTS WRITTEN TO:", results_dir / "interactions.csv")
    plip_results_df = plip_results_df.collect()
    plip_results_df.write_csv(
        file=(results_dir / "interactions.csv"),
    )

    run_data["name"] = top_file.parent.name
    run_data["alignment_scores"] = scores

    ligands_arr = []
    for lig, info in lig_info.items():
        # we try inchikey from the structure, if not found, we check for version with neutral protonation
        id = inchikey_to_chebiID.get(info[1], None)
        name = inchikey_to_name.get(info[1], None)
        print(f"INCHIKEY LOOKUP: {info[1]}, RESULTS: {id}, {name}")
        if id is None or name is None:
            neutral_molecule_inchikey = info[1][:-1] + "N"
            id = inchikey_to_chebiID.get(neutral_molecule_inchikey, None)
            name = inchikey_to_name.get(neutral_molecule_inchikey, None)
            print(
                f"USED NEUTRAL INCHIKEY: {neutral_molecule_inchikey}, got {name}, {id}"
            )
        ligands_arr.append(
            {
                "id": id,
                "ident": lig,
                "name": name,
                "img": "",
                "smiles": info[0],
                "inchikey": info[1],
            }
        )

    run_data["ligands"] = ligands_arr

    run_data |= {"tables": [], "interaction_graphs": [], "maps": []}

    for lig, info in lig_info.items():
        lig_df = plip_results_df.filter(
            pl.concat_str(["lig_name", "lig_pos"], separator="") == lig
        )
        run_data["tables"].append(
            {"graph": create_getcontacts_table(lig_df), "identifier": lig}
        )
        run_data["interaction_graphs"].append(
            {"graph": create_interaction_area_graph(lig_df), "identifier": lig}
        )
        run_data["maps"].append(
            {"graph": create_time_resolved_map(lig_df), "identifier": lig}
        )

    with open(results_dir / "run_data.json", "w") as f:
        json.dump(run_data, f)

    print("Analysis finished! Results available at: ", results_dir, flush=True)

    return run_data


def analyse_group(results_dirs: list[Path], group_result_dir: Path):
    sims_data = []
    for dir in results_dirs:
        with open(dir / "run_data.json") as f:
            raw = f.read()
            data = json.loads(raw)
            sims_data.append(data)

    interactions = []
    for dir in results_dirs:
        with open(dir / "interactions.csv") as f:
            interactions.append(
                (
                    dir.name,
                    pd.read_csv(f),
                )
            )

    with open(group_result_dir / "exp_data.csv") as f:
        exp_data = pd.read_csv(f)

    prepared_dfs = []
    for id, df in interactions:
        sim_name = exp_data.loc[
            exp_data["Simulation ID"] == id, "Simulation name"
        ].iloc[0]
        if len(exp_data.columns.tolist()) > 2:
            value_name = exp_data.columns.tolist()[2]
            value = exp_data.loc[exp_data["Simulation ID"] == id, value_name].iloc[0]
            df[value_name] = value
        df["Simulation name"] = sim_name
        df["Simulation ID"] = id
        prepared_dfs.append(df)

    group_df = pd.concat(prepared_dfs)
    group_df.to_csv(group_result_dir / "group.csv", index=False)

    interaction_freq_map = plot_contact_fraction_heatmap(group_df)

    group_data = {
        "exp_data": exp_data.to_dict(orient="split", index=False),
        "interaction_freq_map": [{"graph": interaction_freq_map}],
    }

    if len(exp_data.columns) > 2:
        interaction_correlation_map, interaction_covariance_map = (
            plot_correlation_covariance_heatmaps(group_df)
        )
        group_data["interaction_correlation_map"] = [
            {"graph": interaction_correlation_map}
        ]
        group_data["interaction_covariance_map"] = [
            {"graph": interaction_covariance_map}
        ]

    with open(group_result_dir / "group_data.json", "w") as f:
        json.dump(group_data, f)

    return None


def _start_simulation(
    top_file: Path,
    traj_file: Path,
    work_dir: Path,
    results_dir: Path,
    frame_count: int | None = None,
):
    # setup for using only specific frames
    print("Starting the simulation!", flush=True)
    if frame_count is None:
        frame_count = get_trajectory_frame_count(top_file, traj_file)
    frames = [x for x in range(frame_count)]
    plip_dir = work_dir / "plip"
    frames_dir = work_dir / "frames"
    sample_dir = work_dir / "sample"
    lig_info = get_interactions_from_trajectory(
        top_file, traj_file, plip_dir, frames_dir, sample_dir, frames
    )
    analyse_simulation(
        top_file, traj_file, lig_info, plip_dir, results_dir, frame_count
    )
    return len(frames)


@task()
def start_simulation(
    top_file: Path,
    traj_file: Path,
    work_dir: Path,
    results_dir: Path,
    frame_count: int | None = None,
):
    return _start_simulation(top_file, traj_file, work_dir, results_dir, frame_count)


example_results_dir = settings.BASE_DIR / "example_results"
example_results_dirnames = []
if example_results_dir.is_dir():
    example_results_dirnames = [dir.name for dir in example_results_dir.iterdir()]


def remove_unused_sim_files(sim_files_dir: Path):
    stat = sim_files_dir.stat()
    last_modified_time = datetime.fromtimestamp(stat.st_ctime)
    if datetime.now() - last_modified_time < timedelta(hours=4):
        return
    try:
        sim = Simulation.objects.get(sim_id=sim_files_dir.name)
        status = sim.get_analysis_status()
        if (
            status != "Queueing"
            and status != "Queued"
            and not status.startswith("Running")
        ):
            shutil.rmtree(sim_files_dir)
            print(f"Removing directory: {sim_files_dir}", flush=True)
    except:
        shutil.rmtree(sim_files_dir)


@periodic_task(crontab(day="*/1"))
def clean_user_uploads():
    print("Running routine cleanup...")
    uploads_dir = settings.BASE_DIR / "user_uploads"
    analysis_dirs = []
    user_dirs = []
    for dir in uploads_dir.iterdir():
        if dir.name in example_results_dirnames:
            continue

        if dir.is_file() and dir.suffix == ".log":
            continue

        if "-" in dir.name:
            analysis_dirs.append(dir)
        else:
            user_dirs.append(dir)

    print("User directories: ", user_dirs)
    print("Analysis directories: ", analysis_dirs)
    for user_dir in user_dirs:
        for subdir in user_dir.iterdir():
            for sim_dir in subdir.iterdir():
                remove_unused_sim_files(sim_dir)
