`use strict`

const modalBackground = document.getElementById("modal-bg");
const modalView = document.getElementById("modal");
const modalGraphPlaceholder = document.getElementById("modal-graph");
const filenameInput = document.getElementById("graph-filename");
const filetypeInput = document.getElementById("graph-filetype");
const widthInput = document.getElementById("graph-width");
const heightInput = document.getElementById("graph-height");

function downloadFile(filename) {
	jobID = window.location.href.split("/").at(-1);
	request_url = `/download/${jobID}/${filename}`;
	const link = document.createElement("a");
	link.href = request_url;
	link.download = `coral_interactions.csv`;
	link.click();
}

function showContent(event) {
	const parent = event.target.closest('.content-window');
	const elem = parent.querySelector('.show-indicator');
	const infoElement = parent.querySelector('.info');
	infoElement.classList.toggle("hidden");
	elem.classList.toggle('rotate-270')
}

async function selectLigand(event) {
	const el = event.target;
	const selectedLigandIdent = el.dataset.ident;
	const ligandSelectable = document.querySelectorAll('.ligand-selectable');

	for (const graphContainer of ligandSelectable) {
		graphContainer.classList.add("hidden")
	}
	const ligandSelected = document.querySelectorAll(`.${selectedLigandIdent}`);

	for (const graphContainer of ligandSelected) {
		graphContainer.classList.remove("hidden")
		const graph = graphContainer.querySelector('.js-plotly-plot');
		const allow_resize = {
			autosize: true
		};
		await Plotly.relayout(graph, allow_resize);
	}

}

addEventListener("DOMContentLoaded", (event) => {
	const firstLigand = document.querySelector('.lig-select')
	if (firstLigand) {
		firstLigand.click()
	}

}
)

let modalGraph = null

async function showPrintView(event) {
	event.stopPropagation()
	const graphToPrint = event.target.closest('.content-window').querySelector('.plotly-graph-div');
	const viewGraph = await Plotly.newPlot('modal-graph', structuredClone(graphToPrint.data), structuredClone(graphToPrint.layout));
	modalView.classList.add("invisible");
	modalBackground.classList.remove("hidden");
	await Plotly.Plots.resize(viewGraph);
	widthInput.value = viewGraph._fullLayout.width;
	heightInput.value = viewGraph._fullLayout.height;
	const prohibit_resize = {
		autosize: false
	};
	await Plotly.relayout(viewGraph, prohibit_resize);
	modalGraph = viewGraph
	modalView.classList.remove("invisible");
	modalBackground.classList.remove("invisible");
}


async function bgClicked(event) {
	try {
		modalView.querySelector(".plot-container").innerHTML = "";
	} catch {

	}
	modalGraph = null;
	modalBackground.classList.add("hidden");
}


function modalClicked(event) {
	console.log("click on modal!");
	event.stopPropagation()
}

function handlePrintViewResize(event) {
	console.log("Resize request!");
}

async function hideExtra() {
	await Plotly.relayout(modalGraph, {
		sliders: [],
		updatemenus: [],
		'xaxis.rangeslider.visible': false
	});
}

function hideBackground() {
	const layout = {
		paper_bgcolor: 'rgba(0,0,0,0)',
		plot_bgcolor: 'rgba(0,0,0,0)',
	};
	console.log(modalGraph.layout);
	console.log(modalGraph.layout.paper_bgcolor);
	console.log(modalGraph.layout.plot_bgcolor);
	Plotly.relayout(modalGraph, layout);
}

function downloadGraph() {
	console.log(filenameInput.value);
	console.log(filetypeInput.value);
	Plotly.downloadImage(modalGraph, {
		format: filetypeInput.value,
		filename: filenameInput.value != "" ? filenameInput.value : "coral_graph",
	});
}

function changePlotWidth() {
	Plotly.relayout(modalGraph, { width: Math.round(widthInput.value) })
}

function changePlotHeight() {
	Plotly.relayout(modalGraph, { height: Math.round(heightInput.value) })
}

async function resizeGraph() {
	const allow_resize = {
		autosize: true
	};
	await Plotly.relayout(modalGraph, allow_resize);
	let width_resized = modalGraph._fullLayout.width;
	let height_resized = modalGraph._fullLayout.height;
	widthInput.value = width_resized;
	heightInput.value = height_resized;

	const set_layout = {
		width: width_resized,
		height: height_resized,
		autosize: false,
	};
	await Plotly.relayout(modalGraph, set_layout);
}

