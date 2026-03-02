import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import polars as pl

PAGE_BG_COLOR = "#e5e7eb"
COMMON_LAYOUT = dict(margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor=PAGE_BG_COLOR)
COMMON_LAYOUT_TABLE = dict(
    margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor=PAGE_BG_COLOR
)


COLUMN_RENAME = {
    "frame": "Frame",
    "int_type": "Interaction type",
    "res_pos": "Residue number",
    "res_name": "Residue name",
    "site_id": "Binding site",
    "lig_chain": "Ligand chain",
    "lig_name": "Ligand name",
    "lig_pos": "Ligand number",
    "res_chain": "Residue chain",
    "aligned_numbering": "Aligned numbering",
}


INTERACTIONS_RENAME = {
    "hydrophobic_interaction": "Hydrophobic",
    "hydrogen_bond": "Hydrogen bond",
    "halogen_bond": "Halogen bond",
    "salt_bridge": "Salt bridge",
    "pi_cation_interaction": "Pi-cation",
    "metal_complex": "Metal complex",
    "water_bridge": "Water bridge",
    "pi_stack": "Pi-pi stacking",
}


INTERACTION_TO_COLOR = {
    "Water bridge": "#B0B0B0",
    "Hydrophobic": "#8da0cb",
    "Pi-pi stacking": "#66c2a5",
    "Pi-cation": "#a6d854",
    "Hydrogen bond": "#ffd92f",
    "Halogen bond": "#fc8d62",
    "Salt bridge": "#e78ac3",
    "Metal complex": "#d6bbd3",
}

INTERACTIONS = list(INTERACTION_TO_COLOR.keys())
COLORS = list(INTERACTION_TO_COLOR.values())


def create_getcontacts_table(df: pl.DataFrame) -> str:

    df = df.select(
        [
            "frame",
            "int_type",
            "res_chain",
            "res_name",
            "res_pos",
        ]
        + ["aligned_numbering"]
        if "aligned_numbering" in df.columns
        else []
    )
    df = df.with_columns(
        pl.col("int_type").cast(pl.String).replace(INTERACTIONS_RENAME)
    ).rename({k: v for k, v in COLUMN_RENAME.items() if k in df.columns})

    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=list(df.columns),
                    line_color=PAGE_BG_COLOR,
                    height=25,
                ),
                cells=dict(
                    values=[s for s in df.iter_columns()],
                    line_color=PAGE_BG_COLOR,
                    height=25,
                ),
            )
        ]
    )
    fig.update_traces(columnwidth=[100, 300])
    fig.update_layout(COMMON_LAYOUT_TABLE)
    table = fig.to_html(
        include_plotlyjs=False,
        full_html=False,
        config={"displaylogo": False, "responsive": True},
    )
    return table


def create_interaction_area_graph(df: pl.DataFrame) -> str:
    df = df.with_columns(
        pl.col("int_type").cast(pl.String).replace(INTERACTIONS_RENAME)
    ).rename({k: v for k, v in COLUMN_RENAME.items() if k in df.columns})

    lo, hi = df.select(
        pl.col("Frame").min().alias("min"), pl.col("Frame").max().alias("max")
    ).row(0)
    frames = np.arange(lo, hi + 1)

    relevant_int_types = df.select("Interaction type").unique()
    all_frames_relevant_interaction_combinations = pl.DataFrame({"Frame": frames}).join(
        relevant_int_types, how="cross"
    )

    interaction_count = (
        df.group_by(["Frame", "Interaction type"])
        .len(name="Count")
        .join(
            all_frames_relevant_interaction_combinations,
            on=["Frame", "Interaction type"],
            how="right",
        )
        .fill_null(0)
    )

    print()
    print(interaction_count, flush=True)
    fig = px.area(
        interaction_count,
        x="Frame",
        y="Count",
        title="Interaction counts",
        line_group="Interaction type",
        color="Interaction type",
        color_discrete_map=INTERACTION_TO_COLOR,
    )

    for int_type in relevant_int_types["Interaction type"]:
        rank = INTERACTIONS.index(int_type)
        print(int_type, rank)
        fig.update_traces(selector=dict(name=int_type), legendrank=rank)

    fig.update_traces(opacity=1.0, selector=dict(fill="tonexty"))
    for trace in fig.data:
        trace.fillcolor = trace.line.color
    fig.update_layout(legend=dict(title="Interaction type", tracegroupgap=2))
    fig.update_layout(xaxis=dict(rangeslider=dict(visible=True), type="linear"))
    fig.update_layout(COMMON_LAYOUT)
    graph = fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"displaylogo": False, "responsive": True},
    )
    return graph


def hex2rgba(hexcol, a):
    return f"rgba({int(hexcol[1:3], 16)},{int(hexcol[3:5], 16)},{int(hexcol[5:7], 16)},{a})"


def create_time_resolved_map(df: pd.DataFrame) -> str:
    df = (
        df.lazy()
        .with_columns(pl.col("int_type").cast(pl.String).replace(INTERACTIONS_RENAME))
        .rename({k: v for k, v in COLUMN_RENAME.items() if k in df.columns})
        .select(["Frame", "Residue name", "Residue number", "Interaction type"])
        .with_columns(
            pl.concat_str(
                [pl.col("Residue name"), pl.col("Residue number")], separator="-"
            ).alias("res_label")
        )
        .collect()
    )

    residues = (
        df.unique(["Residue number", "res_label"])
        .sort("Residue number")["res_label"]
        .to_list()
    )

    relevant_int_types = sorted(
        df.select("Interaction type").unique()["Interaction type"].to_list(),
        key=lambda x: INTERACTIONS.index(x),
    )
    print(relevant_int_types)

    lo, hi = df.select(
        pl.col("Frame").min().alias("min"), pl.col("Frame").max().alias("max")
    ).row(0)
    frames = np.arange(lo, hi + 1)

    all_residue_frame_combinations = (
        df.lazy()
        .select(pl.col("res_label"))
        .unique()
        .join(pl.LazyFrame({"Frame": frames}), how="cross")
    )

    int_counts = (
        df.lazy()
        .group_by(["res_label", "Frame", "Interaction type"])
        .len(name="count")
        .pivot(
            index=["res_label", "Frame"],
            on="Interaction type",
            on_columns=relevant_int_types,
            values="count",
        )
        .join(all_residue_frame_combinations, on=["res_label", "Frame"], how="right")
        .fill_null(0)
        .sort(
            pl.col("res_label").str.split("-").list.last().str.to_integer(),
            pl.col("Frame"),
        )
        .collect()
    )

    vals = (
        int_counts.select(relevant_int_types)
        .to_numpy()
        .reshape(len(residues), len(frames), len(relevant_int_types))
    )

    fig = go.Figure()

    hovertemplate = "Residue: %{y}<br>Frame: %{x}<br>"
    for idx, int_type in enumerate(relevant_int_types):
        hovertemplate += f"{int_type}: %{{customdata[{idx}]}}<br>"

    hovertemplate += "<extra></extra>"

    for k, t in enumerate(relevant_int_types):
        presence = (vals[..., k] > 0).astype(float)
        fig.add_trace(
            go.Heatmap(
                z=presence,
                x=frames,
                y=residues,
                zmin=0,
                zmax=1,
                showscale=False,
                showlegend=False,
                colorscale=[
                    [0.0, hex2rgba(INTERACTION_TO_COLOR[t], 0.0)],
                    [1.0, hex2rgba(INTERACTION_TO_COLOR[t], 1.0)],
                ],
                name=t,
                legendgroup=t,
                customdata=vals,
                hovertemplate=hovertemplate,
            )
        )

    for k, t in enumerate(relevant_int_types):
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                stackgroup=1,
                marker=dict(color=INTERACTION_TO_COLOR[t], size=10),
                fillcolor=INTERACTION_TO_COLOR[t],
                name=t,
                legendgroup=t,
                showlegend=True,
                hoverinfo="skip",
            )
        )

    fig.update_layout(legend=dict(title="Interaction type", tracegroupgap=2))
    fig.update_layout(xaxis=dict(rangeslider=dict(visible=True), type="linear"))
    fig.update_layout(
        COMMON_LAYOUT,
        plot_bgcolor=PAGE_BG_COLOR,
        xaxis_title="Frame",
        yaxis_title="Residue",
        height=700,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)

    graph = fig.to_html(
        include_plotlyjs=False,
        full_html=False,
        config={"displaylogo": False, "responsive": True},
    )
    return graph


def _reslabel(name, num):
    return f"{name}-{num}"


def _resnum_key(label):
    try:
        return int(str(label).split("-")[-1])
    except Exception:
        return 1e9


def contact_fraction_matrix(
    group_df: pd.DataFrame, itype: str | None = None
) -> pd.DataFrame:
    df = group_df.copy()
    df = df.rename(columns=COLUMN_RENAME).replace(
        {"Interaction type": INTERACTIONS_RENAME}
    )

    df["ResidueLabel"] = [
        _reslabel(rn, rr) for rn, rr in zip(df["Residue name"], df["Residue number"])
    ]
    total_frames = (
        df.groupby("Simulation name")["Frame"].nunique().rename("total_frames")
    )

    if itype is not None:
        df = df[df["Interaction type"] == itype]

    df["Frame"] = pd.to_numeric(df["Frame"], errors="coerce")
    df = df.dropna(subset=["Frame", "Simulation name", "ResidueLabel"])

    pres = (
        df[["Simulation name", "ResidueLabel", "Frame"]]
        .drop_duplicates()
        .groupby(["Simulation name", "ResidueLabel"])
        .agg(frames_with_contact=("Frame", "nunique"))
        .reset_index()
    )

    pres = pres.merge(total_frames, on="Simulation name", how="left")

    pres["FractionPercent"] = 100.0 * pres["frames_with_contact"] / pres["total_frames"]

    mat = pres.pivot(
        index="Simulation name", columns="ResidueLabel", values="FractionPercent"
    ).fillna(0.0)

    mat = mat[sorted(mat.columns, key=_resnum_key)]

    return mat


def plot_contact_fraction_heatmap(
    group_df: pd.DataFrame,
    title_prefix: str = "Interaction occurence per residue",
    colorscale: str = "magma_r",
):
    group_df = group_df.rename(columns=COLUMN_RENAME).replace(
        {"Interaction type": INTERACTIONS_RENAME}
    )
    types = [t for t in pd.unique(group_df["Interaction type"]) if pd.notna(t)]
    types_sorted = sorted(types)

    mats = {"All types": contact_fraction_matrix(group_df, None)}
    for t in types_sorted:
        mats[t] = contact_fraction_matrix(group_df, t)

    all_sims = sorted(set().union(*[set(m.index) for m in mats.values()]))
    all_res = sorted(
        set().union(*[set(m.columns) for m in mats.values()]), key=_resnum_key
    )

    for k in mats:
        mats[k] = mats[k].reindex(index=all_sims, columns=all_res, fill_value=0.0)

    init_key = "All types"
    Z0 = mats[init_key].values
    X = all_res
    Y = all_sims

    fig = go.Figure(
        data=go.Heatmap(
            z=Z0,
            x=X,
            y=Y,
            zmin=0,
            zmax=100,
            colorscale=colorscale,
            colorbar=dict(
                title=dict(
                    text="% of trajectory",
                    side="right",
                ),
                tickfont=dict(size=10),
                xpad=10,
            ),
            hovertemplate="Simulation: %{y}<br>Residue: %{x}<br>Fraction: %{z:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        paper_bgcolor=PAGE_BG_COLOR,
        title=f"{title_prefix} — {init_key}",
        xaxis_title="Residue",
        yaxis_title="Simulation",
        xaxis=dict(tickangle=270),
    )

    buttons = []
    for key in [init_key] + types_sorted:
        buttons.append(
            dict(
                label=key,
                method="update",
                args=[
                    {"z": [mats[key].values]},
                    {"title": {"text": f"{title_prefix} — {key}"}},
                ],
            )
        )

    fig.update_xaxes(tickangle=45)

    fig.update_layout(
        updatemenus=[
            dict(
                type="dropdown",
                buttons=buttons,
                x=1.02,
                y=1.15,
                xanchor="left",
                yanchor="top",
                bgcolor=PAGE_BG_COLOR,
                bordercolor="lightgray",
            )
        ]
    )

    fig_html = fig.to_html(
        include_plotlyjs=False,
        full_html=False,
        config={"displaylogo": False, "responsive": True},
    )
    return fig_html


IDENTIFIER_COLUMN = "Simulation name"


def plot_correlation_covariance_heatmaps(
    df: pd.DataFrame,
    colorscale: str = "magma_r",
):
    df = df.rename(columns=COLUMN_RENAME).replace(
        {"Interaction type": INTERACTIONS_RENAME}
    )
    sims_exp_data = df[df.columns[-3:]].drop_duplicates().reset_index(drop=True)
    sims_frame_data = df[df.columns[:-3].to_list() + [IDENTIFIER_COLUMN]]
    sims_frame_data["residue"] = (
        sims_frame_data["Residue name"]
        + "-"
        + sims_frame_data["Residue number"].astype(str)
    )

    interactions_by_sim = (
        sims_frame_data.groupby([IDENTIFIER_COLUMN, "Interaction type"])["Frame"]
        .count()
        .reset_index()
    )
    interactions_by_sim_residue = (
        sims_frame_data.groupby([IDENTIFIER_COLUMN, "residue"])["Frame"]
        .count()
        .reset_index()
    )
    interactions_by_sim_residue_type = (
        sims_frame_data.groupby([IDENTIFIER_COLUMN, "residue", "Interaction type"])[
            "Frame"
        ]
        .count()
        .reset_index()
    )

    interactions_with_exp = interactions_by_sim.merge(sims_exp_data.iloc[:, :-1])
    EXP_DATA_COLUMN = interactions_with_exp.columns.to_list()[-1]

    correlations = {}
    wide_df = interactions_by_sim_residue.pivot_table(
        index=["Simulation name"], columns="residue", values="Frame"
    ).reset_index()
    wide_df = wide_df.merge(sims_exp_data.iloc[:, :-1])
    corrs = wide_df.corr(numeric_only=True)[EXP_DATA_COLUMN].sort_values(
        ascending=False
    )
    correlations["Overall"] = corrs

    for interaction in interactions_by_sim_residue_type["Interaction type"].unique():
        wide_df = (
            interactions_by_sim_residue_type[
                interactions_by_sim_residue_type["Interaction type"] == interaction
            ]
            .pivot_table(index=["Simulation name"], columns="residue", values="Frame")
            .reset_index()
        )
        wide_df = wide_df.merge(sims_exp_data.iloc[:, :-1])
        corrs = wide_df.corr(numeric_only=True)[EXP_DATA_COLUMN].sort_values(
            ascending=False
        )
        corrs.drop(EXP_DATA_COLUMN, inplace=True)
        correlations[interaction] = corrs

    corrs_df = pd.DataFrame(correlations)
    corrs_df.drop(EXP_DATA_COLUMN, inplace=True)
    corrs_df.sort_index(key=lambda x: x.str.split("-").str[1].astype(int), inplace=True)
    corrs_df.fillna("", inplace=True)

    fig_corr = go.Figure(
        data=go.Heatmap(
            z=corrs_df.T.values,
            x=corrs_df.index,
            y=corrs_df.columns.to_list(),
            zmin=-1,
            zmax=1,
            colorscale="rdylbu_r",
            colorbar=dict(
                title=dict(
                    text="Correlation",
                    side="right",
                ),
                tickfont=dict(size=10),
                xpad=10,
            ),
            hovertemplate="Residue: %{x}<br>Correlation: %{z}<extra></extra>",
        )
    )

    fig_corr.update_layout(
        paper_bgcolor=PAGE_BG_COLOR,
        title=f"Correlation between number of interactions and {EXP_DATA_COLUMN}",
        xaxis_title="Residue",
        yaxis_title="Interaction type",
        xaxis=dict(tickangle=270),
    )

    fig_corr.update_xaxes(tickangle=45)

    fig_corr_html = fig_corr.to_html(
        include_plotlyjs=False,
        full_html=False,
        config={"displaylogo": False, "responsive": True},
    )

    covariances = {}
    print(wide_df, flush=True)
    covs = wide_df.cov(numeric_only=True)[EXP_DATA_COLUMN].sort_values(ascending=False)
    covariances["Overall"] = covs
    print(covs, flush=True)

    for interaction in interactions_by_sim_residue_type["Interaction type"].unique():
        wide_df = (
            interactions_by_sim_residue_type[
                interactions_by_sim_residue_type["Interaction type"] == interaction
            ]
            .pivot_table(index=["Simulation name"], columns="residue", values="Frame")
            .reset_index()
        )
        wide_df = wide_df.merge(sims_exp_data.iloc[:, :-1])
        covs = wide_df.cov(numeric_only=True)[EXP_DATA_COLUMN].sort_values(
            ascending=False
        )
        covs.drop(EXP_DATA_COLUMN, inplace=True)
        covariances[interaction] = covs

    covs_df = pd.DataFrame(covariances)
    covs_df.drop(EXP_DATA_COLUMN, inplace=True)
    covs_df.sort_index(key=lambda x: x.str.split("-").str[1].astype(int), inplace=True)
    covs_df.fillna("", inplace=True)

    fig_cov = go.Figure(
        data=go.Heatmap(
            z=covs_df.T.values,
            x=covs_df.index,
            y=covs_df.columns.to_list(),
            zmin=covs_df.min(numeric_only=True).min(),
            zmax=covs_df.max(numeric_only=True).max(),
            colorscale="rdylbu_r",
            colorbar=dict(
                title=dict(
                    text="Covariance",
                    side="right",
                ),
                tickfont=dict(size=10),
                xpad=10,
            ),
            hovertemplate="Residue: %{x}<br>Covariance: %{z}<extra></extra>",
        )
    )

    fig_cov.update_layout(
        paper_bgcolor=PAGE_BG_COLOR,
        title=f"Covariance between number of interactions and {EXP_DATA_COLUMN}",
        xaxis_title="Residue",
        yaxis_title="Interaction type",
        xaxis=dict(tickangle=270),
    )

    fig_cov.update_xaxes(tickangle=45)

    fig_cov_html = fig_cov.to_html(
        include_plotlyjs=False,
        full_html=False,
        config={"displaylogo": False, "responsive": True},
    )

    return fig_corr_html, fig_cov_html
