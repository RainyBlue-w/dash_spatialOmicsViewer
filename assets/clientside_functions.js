
const pick = (obj, arr) =>
    arr.reduce((iter, val) => (val in obj && iter.push(obj[val]), iter), [])

const getItem = (arr, key) =>
    arr.reduce((iter, val) => (iter.push(val[key]), iter), [])

const getObjFirstItem = (obj) => {
    for(let i in obj) return obj[i];
}

function plot_expScatter3D(obs, cells, singleExp, mixcolor, ifmulti, hideAxes) {

    var filtObs = pick(obs, cells)
    if (!ifmulti) {
        var colors = pick(singleExp, cells)
        var colors = colors.reduce((iter, val) => (iter.push(Object.values(val)[0]), iter), [])
    } else {
        var colors = pick(mixcolor, cells)
    }

    var figExp = {
        'data': [
            {
                x: filtObs.map(obj => obj['x']), y: filtObs.map(obj => obj['y']), z: filtObs.map(obj => obj['z']),
                mode: 'markers', type: 'scatter3d',
                marker: {
                    color: colors, coloraxis: 'coloraxis', size: 3, opacity: 1,
                }
            }
        ],
        'layout': {
            'plot_bgcolor': '#ffffff',
            'coloraxis': {
                'colorscale': [
                    [0.00, "rgb(244,244,244)"],
                    [0.05, "rgb(244, 244, 244)"],
                    [1.00, "rgb(34, 94, 168)"],
                ],
            },
            // 'uirevision': 'constant',
            margin: {l: 10, r: 0, t: 0, b: 0},
            scene: {
                xaxis: {
                    'visible': !hideAxes,
                    'backgroundcolor': "white", 'showbackground': true, 'zerolinecolor': 'grey', 'fixedrange': true, 'gridcolor': 'grey', 'nticks': 6
                },
                yaxis: {
                    'visible': !hideAxes,
                    'backgroundcolor': "white", 'showbackground': true, 'zerolinecolor': 'grey', 'fixedrange': true, 'gridcolor': 'grey', 'nticks': 6
                },
                zaxis: {
                    'visible': !hideAxes,
                    'backgroundcolor': "white", 'showbackground': true, 'zerolinecolor': 'grey', 'fixedrange': true, 'gridcolor': 'grey', 'nticks': 6
                },
                bgcolor: 'white'
            }
        }
    }

    return figExp
}

function plot_ctpScatter3D(obs, cells, ctp_cmap, hideAxes){
    var filtObs = pick(obs, cells)
    var filtObs_group = filtObs.groupBy(({ celltype }) => celltype)
    var figCtp = {
        'data': [],
        'layout': {
            'plot_bgcolor': '#ffffff',
            // 'uirevision': 'constant',
            legend: {
                title: { text: 'Celltype' },
                itemsizing: 'constant',
                tracegroupgap: 0,
            },
            margin: {l: 0, r: 10, t: 0, b: 0,},
            scene: {
                xaxis: {
                    'visible': !hideAxes,
                    'backgroundcolor': "white", 'showbackground': true, 'zerolinecolor': 'grey', 'fixedrange': true, 'gridcolor': 'grey', 'nticks': 6
                },
                yaxis: {
                    'visible': !hideAxes,
                    'backgroundcolor': "white", 'showbackground': true, 'zerolinecolor': 'grey', 'fixedrange': true, 'gridcolor': 'grey', 'nticks': 6
                },
                zaxis: {
                    'visible': !hideAxes,
                    'backgroundcolor': "white", 'showbackground': true, 'zerolinecolor': 'grey', 'fixedrange': true, 'gridcolor': 'grey', 'nticks': 6
                },
                bgcolor: 'white'
            },
        }
    }
    for (let ctp in filtObs_group) {
        let filt = filtObs_group[ctp]
        figCtp['data'].push(
            {
                x: filt.map(obj => obj['x']),
                y: filt.map(obj => obj['y']),
                z: filt.map(obj => obj['z']),
                mode: 'markers',
                type: 'scatter3d',
                legendgroup: ctp,
                name: ctp,
                showlegend: true,
                marker: {
                    color: ctp_cmap[ctp],
                    size: 3,
                    opacity: 1,
                },
            }
        )
    }
    return figCtp
}

function push_previewBox(fig, preview, preRange){
    if (preview) {
        var preview_box = {
            x: [preRange['x_min'], preRange['x_min'], preRange['x_min'], preRange['x_min'],
            preRange['x_max'], preRange['x_max'], preRange['x_max'], preRange['x_max']],
            y: [preRange['y_min'], preRange['y_max'], preRange['y_min'], preRange['y_max'],
            preRange['y_min'], preRange['y_max'], preRange['y_min'], preRange['y_max']],
            z: [preRange['z_min'], preRange['z_min'], preRange['z_max'], preRange['z_max'],
            preRange['z_min'], preRange['z_min'], preRange['z_max'], preRange['z_max']],
            i: [0, 1, 0, 0, 0, 0, 2, 2, 7, 7, 7, 7],
            j: [1, 2, 4, 1, 4, 2, 3, 6, 4, 4, 1, 1],
            k: [2, 3, 5, 5, 6, 6, 7, 7, 6, 5, 3, 5],
            color: 'black', opacity: 0.60, type: 'mesh3d'
        }
    } else {
        var preview_box = {
            x: [], y: [], z: [], i: [], j: [], k: [], type: 'mesh3d', color: 'black', opacity: 0.60
        }
    }
    fig['data'].push(preview_box)
    return fig
}

window.dash_clientside = Object.assign({}, window.dash_clientside, {
    plotFunc_3Dtab: {
        store_previewRange: function (x_range, y_range, z_range) {
            console.log(z_range)
            var dict = {
                'x_min': x_range[0], 'x_max': x_range[1],
                'y_min': y_range[0], 'y_max': y_range[1],
                'z_min': z_range[0], 'z_max': z_range[1],
            }
            return dict
        },

        exp_3Dscatter: function(obs, obsFilter, expFilter, ctpFilter, singleExp, ifmulti, mixcolor, hideAxes, preview, preRange){
            tid = window.dash_clientside.callback_context.triggered.map((obj) => (obj['prop_id']))
            console.log('func: exp_3Dscatter:', tid);

            if (expFilter) {
                var expSet = new Set(expFilter)
                var cells = obsFilter.filter(item => expSet.has(item))
            } else {
                var cells = obsFilter
            }

            var ctpSet = new Set(ctpFilter)
            cells = cells.filter(item => ctpSet.has(item))

            figExp = plot_expScatter3D(obs, cells, singleExp, mixcolor, ifmulti, hideAxes)
            figExp = push_previewBox(figExp, preview, preRange, hideAxes)

            return figExp
        },

        ctp_3Dscatter: function (obs, obsFilter, expFilter, hideAxes, preview, preRange, ctp_cmap){
            tid = window.dash_clientside.callback_context.triggered.map((obj) => (obj['prop_id']))
            console.log('func: ctp_3Dscatter:', tid);

            if (expFilter) {
                var expSet = new Set(expFilter)
                var cells = obsFilter.filter(item => expSet.has(item))
            } else {
                var cells = obsFilter
            }

            figCtp = plot_ctpScatter3D(obs, cells, ctp_cmap, hideAxes)
            figCtp = push_previewBox(figCtp, preview, preRange, hideAxes)

            return figCtp
        },

        singleExpCtp_violin: function (obs, obsFilter, expFilter, singleExp, ifmulti, ctp_map){
            if (expFilter) {
                var expSet = new Set(expFilter)
                var intersection = obsFilter.filter(item => expSet.has(item))
            } else {
                var intersection = obsFilter
            }

            var filtObs = pick(obs, intersection)
            var expValue = pick(singleExp, intersection).reduce( (iter,val) => (iter.push(Object.values(val)[0]), iter), [] )

            var name = Object.keys(getObjFirstItem(singleExp))[0]
            var ncells = intersection.length
            var figExp = {
                'data': [{
                    x: expValue, y0: name+"("+ncells +")",  type: 'violin',
                    fillcolor: 'lightseagreen', opacity: 0.6, pointpos: 1.5, jitter: 0.2,
                    orientation: 'h', side: 'positive', points: 'all',
                    name: name,
                    marker: {size: 2.5}, box: { visible: true }, line: {color: 'black'},
                    meanline: { visible: true }, hoverInfo: 'none', hoveron: false,
                }],
                'layout': {
                    plot_bgcolor: 'rgba(200,200,200,0.15)',
                    xaxis: {dtick:1, showgrid: false},
                    yaxis: {showgrid: true},
                    margin: {
                        l: 80, r: 20, t: 80, b: 80
                    },
                }
            }

            var figCtp = {
                data: [],
                layout: {
                    plot_bgcolor: 'rgba(200,200,200,0.15)',
                    xaxis: {dtick: 1, gridcolor: '#ffffff', gridwidth: 1, griddash: 'solid'},
                    yaxis: {gridcolor: 'rgba(200,200,200,0.6)', gridwidth: 1.2},
                    legend: {
                        title: {text: 'Celltype'}, tracegroupgap: 0,
                    },
                    margin: {
                        l: 200, r: 0, t: 10, b: 40,
                    },
                    height: 800,
                }
            }

            filtObs.map( (obj, index) => obj['exp']=expValue[index] )
            var filtObs_group = filtObs.groupBy(({ celltype }) => celltype)

            for (let ctp in filtObs_group) {
                let filt = filtObs_group[ctp]
                figCtp['data'].push(
                    {
                        x: filt.map(obj => obj['exp']), x0: '', xaxis: 'x',
                        y: filt.map(obj => obj['celltype']), y0: '', yaxis: 'y',
                        jitter: 0.2, width: 1.3, side: 'positive', orientation: 'h',
                        name: ctp, legendgroup: ctp, offsetgroup: ctp, scalegroup: true,
                        showlegend: true,
                        marker: { size: 2.5, color: ctp_map[ctp] },
                        type: 'violin', hoverInfo: 'none', hoveron: true,
                    }

                )
            }



            return [figExp, figCtp]
        },

        multiExpCtp_violin: function (obs, obsFilter, expFilter, multiExp, ifmulti, ctp_map){

        }
    }
});