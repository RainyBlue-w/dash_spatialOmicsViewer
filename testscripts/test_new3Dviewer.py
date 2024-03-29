#!/usr/bin/env python
# coding: utf-8

# import dash
# dash.register_page(__name__, path='/')

# In[] env
from math import isnan
import math
from tkinter.font import names
from dash import Dash, dcc, html, dash_table, Input, Output, callback, no_update, State, Patch, DiskcacheManager, clientside_callback, ctx
from dash.dash_table.Format import Format, Group, Scheme, Symbol
from dash.exceptions import PreventUpdate
import dash_daq as daq
import dash_ag_grid as dag

import plotly.express as px
import plotly.graph_objects as go
import plotly
from plotly.subplots import make_subplots
from plotnine import *
import plotnine.options

from PIL import Image
import dash_bootstrap_components as dbc
import scanpy as sc
import os
import pandas as pd
import dask.dataframe as dd
import numpy as np
# import loompy as lp
import h5py
import json

import squidpy as sq

from matplotlib import cm
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
import matplotlib.pyplot as plt
import re
import seaborn as sns
from concurrent import futures
from typing import List, Dict, Tuple
import diskcache
background_callback_manager = DiskcacheManager(diskcache.Cache("/rad/wuc/dash_data/spatial/cache"))



# In[] data

exp_data = {
  'E7.5': sc.read_h5ad("/rad/wuc/dash_data/spatial/matrix_data/E7.5_HC0.5_min400.h5ad"),
  'E7.75': sc.read_h5ad("/rad/wuc/dash_data/spatial/matrix_data/E7.75_HC0.5_min400.h5ad"),
  'E8.0': sc.read_h5ad("/rad/wuc/dash_data/spatial/matrix_data/E8.0_HC0.5_min400.h5ad")
}

for stage,data in exp_data.items():
    data.obs.celltype = pd.Categorical(data.obs.celltype)

coord_data = {
  'E7.5': pd.read_csv('/rad/wuc/dash_data/spatial/spatial_coordinate.embryo_E7.5.csv', sep=' '),
  'E7.75': pd.read_csv('/rad/wuc/dash_data/spatial/spatial_coordinate.embryo_E7.75.csv', sep=' '),
  'E8.0': pd.read_csv('/rad/wuc/dash_data/spatial/spatial_coordinate.embryo_E8.0.csv', sep=' ')
}

for stage in exp_data.keys():
  exp_data[stage].obs[['x','y','z','x_flatten', 'y_flatten']] = coord_data[stage].loc[exp_data[stage].obs_names,['x','y','z','x_flatten', 'y_flatten']]

for stage in exp_data.keys():
  exp_data[stage].raw = exp_data[stage].copy()
  sc.pp.normalize_total(exp_data[stage], target_sum=1e4)
  sc.pp.log1p(exp_data[stage])
  exp_data[stage].obsm = {'X_spatial': coord_data[stage].loc[exp_data[stage].obs_names,['x','y','z']]}

for k,v in exp_data.items():
  v.obs.germ_layer = [i.replace('exe-ecto', 'ectoderm') for i in v.obs.germ_layer.values]

auc_data = {}
regulon_geneset = {}
for stage in ['E7.5', 'E7.75', 'E8.0']:
  h5 = h5py.File( '/rad/wuc/dash_data/spatial/matrix_data/%s_auc_mtx.h5' % (stage))
  auc_mtx = pd.DataFrame(h5['auc_matrix'], index=h5['cell'][:].astype(str), columns=h5['regulon'][:].astype(str))
  auc_data[stage] = sc.AnnData(X=auc_mtx, obs=exp_data[stage].obs)
  regulon_geneset[stage] = json.loads(h5['geneset'][()])
  h5.close()
del(auc_mtx)

genes_min_pval = pd.read_csv("/rad/wuc/dash_data/spatial/sparkX_res/genes_padj_minVal.csv",
                             header=[0], index_col=[0,1]) 


genes_all_pval = pd.read_csv("/rad/wuc/dash_data/spatial/sparkX_res/genes_padj_combine.csv",
                             header=[0,1], index_col=[0,1]) 
genes_all_pval = genes_all_pval.loc[:,[('ecto', 'adjustedPval'), ('meso', 'adjustedPval'), ('endo', 'adjustedPval'), ('all', 'adjustedPval')]]
genes_all_pval.columns = ['ecto p.adj', 'meso p.adj', 'endo p.adj', 'all p.adj']
genes_all_pval = genes_all_pval.groupby(level=0, group_keys=False
                                               ).apply(lambda x: x.sort_values(by='all p.adj'))
ctp_cmap = pd.read_csv("/rad/wuc/dash_data/spatial/celltype_cmap.csv")
ctp_cmap = dict(zip(ctp_cmap['celltype'], ctp_cmap['Epiblast']))



# In[] functions

def show_celltype_spatial(adata, embedding, cmap = ctp_cmap, **kws):
  embedding = embedding.loc[adata.obs_names,:]
  pdf = pd.DataFrame(np.array(embedding), 
                    index=adata.obs_names, 
                    columns=['x', 'y'])
  pdf = pd.concat([pdf, adata.obs[['celltype','germ_layer']]], axis=1)
  pdf = pdf.sort_values(by='celltype')
  plot = px.scatter(
    data_frame = pdf,
    x = 'x', y = 'y', color = 'celltype',
    color_discrete_map = cmap,
    **kws
  )
  plot.update_yaxes(visible=False)
  plot.update_xaxes(visible=False)
  plot.update_traces(marker_size=4.5,
                    marker_opacity=1)
  plot.update_layout(
    margin=dict(l=10, r=10, t=30, b=0),
    plot_bgcolor = '#ffffff', 
    uirevision='constant',
    legend_itemsizing = 'constant'
  )
  plot.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1],
                                      font_size = 20)) 

  return plot

def show_feature_spatial(adata, feature, embedding, cmap = None, sort=False, ascending=True, **kws):
    embedding = embedding.loc[adata.obs_names,:]
    if cmap is None:
        cmap = [(0.00, "rgb(244,244,244)"),
                (0.05, "rgb(244, 244, 244)"),
                (1.00, "rgb(34, 94, 168)")
                ]
    pdf = pd.DataFrame(np.array(embedding), 
                       index=adata.obs_names, 
                       columns=['x', 'y'])
    pdf = pd.concat([pdf, adata[:,feature].to_df(), adata.obs['germ_layer']], axis=1)
    if sort is True:
      pdf = pdf.sort_values(by=feature, ascending=ascending)
    plot = px.scatter(
        data_frame = pdf,
        x = 'x', y = 'y', color = feature,
        color_continuous_scale = cmap,
        **kws
      )
    plot.update_yaxes(visible=False)
    plot.update_xaxes(visible=False)
    plot.update_traces(marker_size=4.5,
                      marker_opacity=0.9)
    plot.update_layout(
      margin=dict(l=10, r=10, t=30, b=0),
      plot_bgcolor = '#ffffff', 
      uirevision='constant',
      coloraxis = {
        'colorbar' : {'tickformat': '4.2f'}
      }
    )
    plot.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1],
                                               font_size = 20)) 
    return plot

def show_celltype_spatial_3D(adata, embedding, cmap = ctp_cmap, **kws):
    embedding = embedding.loc[adata.obs_names,:]
    pdf = pd.DataFrame(np.array(embedding), 
                       index=adata.obs_names, 
                       columns=['x', 'y', 'z'])
    pdf = pd.concat([pdf, adata.obs['celltype']], axis=1)
    pdf = pdf.sort_values(by='celltype')
    plot = px.scatter_3d(
        data_frame = pdf,
        x = 'x', y = 'y', z='z',
        color = 'celltype',
        color_discrete_map=cmap,
        **kws
      )
    plot.update_traces(marker_size=3,
                      marker_opacity = 1)
    plot.update_layout(
      margin=dict(l=10, r=10, t=30, b=0),
      uirevision='constant',
      legend_itemsizing = 'constant',
    )
    
    plot.update_layout(
      scene = dict(
        xaxis = {
                'visible': True,
                'backgroundcolor' :"white",
                'showbackground': True,
                'zerolinecolor': 'grey',
                'gridcolor': 'grey',
                'nticks': 6},
        yaxis = {
                'visible': True,
                'backgroundcolor' :"white",
                'showbackground': True,
                'zerolinecolor': 'grey',
                'gridcolor': 'grey',
                'nticks': 6},
        zaxis = {
                'visible': True,
                'backgroundcolor' :"white",
                'showbackground': True,
                'zerolinecolor': 'grey',
                'gridcolor': 'grey',
                'nticks': 6},
        bgcolor = 'white'
      )
    )
    plot.add_trace(go.Mesh3d(x=[0,0], y=[0,0], z=[0,0]))
    
    return plot

def show_feature_spatial_3D(adata, feature, embedding, cmap = None, sort=False, ascending=True, **kws):
    embedding = embedding.loc[adata.obs_names,:]
    if cmap is None:
        cmap = [(0.00, "rgb(244,244,244)"),
                (0.05, "rgb(244, 244, 244)"),
                (1.00, "rgb(34, 94, 168)")
                ]
    pdf = pd.DataFrame(np.array(embedding), 
                       index=adata.obs_names, 
                       columns=['x', 'y', 'z'])
    pdf = pd.concat([pdf, adata[:,feature].to_df()], axis=1)
    if sort is True:
      pdf = pdf.sort_values(by=feature, ascending=ascending)
    plot = px.scatter_3d(
        data_frame = pdf,
        x = 'x', y = 'y', z='z',
        color = feature,
        color_continuous_scale = cmap,
        **kws
      )
    plot.update_traces(marker_size=3,
                      marker_opacity = 0.8)
    plot.update_layout(
      margin=dict(l=10, r=10, t=30, b=0),
      uirevision='constant',
      coloraxis = {
        'colorbar' : {'tickformat': '4.2f'}
      }
    )
    
    plot.update_layout(
      scene = dict(
        xaxis = {
                'visible': True,
                'backgroundcolor' :"white",
                'showbackground': True,
                'zerolinecolor': 'grey',
                'gridcolor': 'grey',
                'nticks': 6},
        yaxis = {
                'visible': True,
                'backgroundcolor' :"white",
                'showbackground': True,
                'zerolinecolor': 'grey',
                'gridcolor': 'grey',
                'nticks': 6},
        zaxis = {
                'visible': True,
                'backgroundcolor' :"white",
                'showbackground': True,
                'zerolinecolor': 'grey',
                'gridcolor': 'grey',
                'nticks': 6},
        bgcolor = 'white'
      )
    )
    plot.add_trace(go.Mesh3d(x=[0,0], y=[0,0], z=[0,0]))
    return plot

def vector_to_rgba(v):
  color = list(v.keys())
  color = [str(math.ceil(v[i])) if i in color else '255' for i in ['R', 'G', 'B'] ]
  if(all([ i=='255' for i in color])):
    rgba = 'rgba(255,255,255,0)'
  else:
    rgba = f'rgba({color[0]}, {color[1]}, {color[2]}, 1)'
    
  return rgba

def multiNames_show_color(adata, genes_dict):
  import numpy
  tmp = {}
  for key,value  in genes_dict.items():
      if value:
          tmp[key] = value
  genes_dict = tmp
  colors = list(genes_dict.keys())
  others = [i for i in ['R', 'G', 'B'] if i not in colors]
  genes = list(genes_dict.values())

  exp = adata[:, genes].to_df()
  exp.columns = colors

  delta = 255 - exp.div(exp.max(axis=0), axis=1)*255
  delta[others] = 255

  def color_geoMean(a,b):
    a = 255-a
    b = 255-b
    geoMean = numpy.sqrt((a**2+b**2)/2)
    # geoMean = ((a**3+b**3)/2)**(1/3)
    color = 255 - geoMean
    return color
  def mean(a,b, c=None):
    if c:
      return (a+b+c)/3
    else:
      return (a+b)/2

  if len(colors)==1:
    color = pd.DataFrame({
        colors[0] : 255,
        others[0] : delta[colors[0]],
        others[1] : delta[colors[0]],
    })
  elif len(colors)==2:
    color = pd.DataFrame({
        colors[0] : delta[colors[1]],
        colors[1] : delta[colors[0]],
        others[0] : color_geoMean(delta[colors[1]],delta[colors[0]]),
    })
  elif len(colors)==3:
    color = pd.DataFrame({
        'R' : color_geoMean(delta['G'], delta['B']),
        'G' : color_geoMean(delta['R'], delta['B']),
        'B' : color_geoMean(delta['R'], delta['G']),
    })
  
  color['RGBA'] = color.apply(vector_to_rgba, axis=1)
  return color['RGBA']

def show_multiFeatures_spatial(adata, features_dict, embedding, **kws):
  
  embedding = embedding.loc[adata.obs_names,:]
  pdf = pd.DataFrame(np.array(embedding), 
                      index=adata.obs_names, 
                      columns=['x', 'y'])
  features = list(features_dict.values())
  pdf = pd.concat([pdf, adata[:,features].to_df(), adata.obs['germ_layer']], axis=1)
  colors = multiNames_show_color(adata, features_dict)
  
  plot = go.Figure()
  plot.add_trace(go.Scatter(
    x = pdf.x, y = pdf.y, mode='markers',
    marker={'color': colors}
  ))
  plot.update_yaxes(visible=False)
  plot.update_xaxes(visible=False)
  plot.update_traces(marker_size=4.5,
                    marker_opacity=1)
  plot.update_layout(
    margin=dict(l=10, r=10, t=30, b=0),
    plot_bgcolor = '#ffffff', 
    uirevision='constant',
  )
  plot.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1],
                                              font_size = 20)) 
  return plot

def show_multiFeatures_spatial_3D(adata, features_dict, embedding, **kws):
  
  embedding = embedding.loc[adata.obs_names,:]
  pdf = pd.DataFrame(np.array(embedding), 
                      index=adata.obs_names, 
                      columns=['x', 'y', 'z'])
  
  features = [i for i in features_dict.values() if i]
  pdf = pd.concat([pdf, adata[:,features].to_df()], axis=1)

  colors = multiNames_show_color(adata, features_dict)
  plot = go.Figure()
  plot.add_trace(go.Scatter3d(
    x = pdf.x, y = pdf.y, z = pdf.z, 
    mode='markers', marker={'color': colors}
  ))
  plot.update_traces(marker_size=3,
                    marker_opacity = 0.9)
  plot.update_layout(
    margin=dict(l=10, r=10, t=30, b=0),
    uirevision='constant',
    coloraxis = {
      'colorbar' : {'tickformat': '4.2f'}
    }
  )
  
  plot.update_layout(
    scene = dict(
      xaxis = {
              'visible': True,
              'backgroundcolor' :"white",
              'showbackground': True,
              'zerolinecolor': 'grey',
              'gridcolor': 'grey',
              'nticks': 6},
      yaxis = {
              'visible': True,
              'backgroundcolor' :"white",
              'showbackground': True,
              'zerolinecolor': 'grey',
              'gridcolor': 'grey',
              'nticks': 6},
      zaxis = {
              'visible': True,
              'backgroundcolor' :"white",
              'showbackground': True,
              'zerolinecolor': 'grey',
              'gridcolor': 'grey',
              'nticks': 6},
      bgcolor = 'white'
    )
  )
  plot.add_trace(go.Mesh3d(x=[0,0], y=[0,0], z=[0,0]))
  return plot

def show_features_spatial_regularExp(adata, stage,  odir, featureType, embedding, pattern=None, features=None,cmap=None, sort=False, ascending=True, dpi=100, **kws):
  embedding = embedding.loc[adata.obs_names,:]
  if not features:
    
    img_dir = '/rad/wuc/dash_data/spatial/tmp/%s/%s/plotFeatureSeries_%s_%s_%s_dpi%d.png' % (odir, stage, stage, pattern, featureType, dpi)
    if os.path.exists( img_dir ):
      return img_dir
    
    features = [i  for i in adata.var_names if re.match(pattern, i)]
    features = [i for i in features if i in genes_min_pval.loc[stage].index.to_list()]

  else:
    img_dir = '/rad/wuc/dash_data/spatial/tmp/%s/%s/plotFeatureSeries_%s_%s_%s_dpi%d.png' % (odir, stage, stage, "tmp", featureType, dpi)

  ordered_features = genes_min_pval.loc[stage].loc[features].sort_values(by='PadjMinVal', ascending=True).index.to_list()

  pdf = pd.DataFrame(np.array(embedding), 
                      index=adata.obs_names, 
                      columns=['x', 'y'])
  
  features_df = adata[:,ordered_features].to_df()
  features_df.columns = ['%s\n(%.2e)' % (i,genes_min_pval.loc[stage].loc[i, 'PadjMinVal']) for i in features_df.columns]

  pdf = pd.concat([pdf, features_df, adata.obs.germ_layer], axis=1)
  pdf = pd.melt(pdf, id_vars = ['x', 'y', 'germ_layer'], var_name='feature', value_name='value')
  if sort:
    pdf = pdf.sort_values(by='value', ascending=ascending)
  pdf['feature'] = pdf['feature'].astype('category').values.reorder_categories(features_df.columns)
  pdf['germ_layer'] = pdf['germ_layer'].astype('category').values.reorder_categories(['ectoderm','mesoderm','endoderm'])

  # plotnine
  (
    ggplot() + 
    geom_point(data = pdf, mapping=aes(x='x', y='y', color='value')) +
    facet_grid('feature ~ germ_layer') + 
    scale_color_gradientn(colors = ['#e0e0e0', '#e0e0e0','#225ea8'], values = [0,0.05,1]) +
    theme(
      # legend_position='top',
      # legend_direction='horizontal',
      axis_title = element_text(size=16),
      axis_text = element_text(size=10),
      panel_grid = element_blank(),
      panel_border = element_rect(linewidth=0.4, fill= 'None'),
      panel_background = element_rect(fill= 'None'),
      strip_text_x = element_text(size=16),
      strip_text_y = element_text(size=16, face = 'bold', angle=0)
    )
  ).save(img_dir, width=12, height=1+3*len(features), dpi=dpi, 
          limitsize=False, verbose=False)
  return img_dir

def show_featuresCtpcounts_spatial_regularExp(adata, stage, odir, featureType, embedding, pattern=None, features=None, cmap=ctp_cmap, sort=False, ascending=True, dpi=150, **kws):
  embedding = embedding.loc[adata.obs_names,:]
  if not features:
    img_dir = '/rad/wuc/dash_data/spatial/tmp/%s/%s/plotFeatureSeries_%s_%s_%s_dpi%d.png' % (odir, stage, stage, pattern, featureType, dpi)
    if os.path.exists( img_dir ):
      return img_dir
    features = [i  for i in adata.var_names if re.match(pattern, i)]
    features = [i for i in features if i in genes_min_pval.loc[stage].index.to_list()]

  else:
    img_dir = '/rad/wuc/dash_data/spatial/tmp/%s/%s/plotFeatureSeries_%s_%s_%s_dpi%d.png' % (odir, stage, stage, "tmp", featureType, dpi)

  ordered_features = genes_min_pval.loc[stage].loc[features].sort_values(by='PadjMinVal', ascending=True).index.to_list()
  
  ctp_counts = {}
  for gene in ordered_features:
    df = adata[:,gene].to_df()
    # thr = df.min()+(df.max()-df.min())*0.05
    df = df[df[gene] > 0]
    counts = pd.DataFrame(adata.obs['celltype'][df.index].value_counts())
    counts['gene'] = gene
    counts['count'] = counts['count']/sum(counts['count'])
    ctp_counts[gene] = counts
  ctp_counts = pd.concat(ctp_counts, axis=0)
  ctp_counts['celltype'] = np.array(ctp_counts.index.to_list())[:,1]
  ctp_counts['text_y'] = ctp_counts['count'].max()/2
  ctp_counts['gene'] = ctp_counts['gene'].astype('category').values.reorder_categories(ordered_features)
  bar_df = ctp_counts[ctp_counts['count']>0].groupby(['gene']).head(5)
  bar_df['ctp_order'] = bar_df['celltype'] +'_' + bar_df['gene'].astype(str)
  bar_df['ctp_order'] = bar_df['ctp_order'].astype('category').values.reorder_categories(bar_df['ctp_order'][::-1])
  (
    ggplot() + 
      geom_bar(data = bar_df, mapping=aes(x='ctp_order', y='count', fill = 'celltype'), stat='summary') +
      facet_grid(
        'gene~.', scales='free_y'
                ) +
      scale_y_continuous( labels = lambda list: [("%.2f%%" % (x*100)) for x in list] ) +
      scale_fill_manual(breaks=list(cmap.keys()),
                        values=list(cmap.values())) +
      guides(
        fill= guide_legend(
          ncol = 1,
          byrow = True
        )
      ) + 
      theme(legend_position='none',
        axis_text_y = element_text(size=12),
        axis_text_x = element_text(size=12),
        axis_title_x = element_blank(),
        axis_ticks_major_x = element_blank(),
        axis_ticks_minor_x = element_blank(),
        axis_title_y=element_blank(),
        strip_text_y = element_text(size=16, face = 'bold', angle=0)
      ) +
      scale_x_discrete(labels = lambda list: [re.search(r'^(.*?)_',x).group(1) for x in list]) + 
      # geom_text(data = ctp_counts[ctp_counts['count'] > 0.05],
      #           mapping = aes(x='celltype', y='text_y', label = 'celltype'),
      #           size=8,
      #           angle=90) + 
      coord_flip()
  ).save(img_dir, width=8, height=1+3*len(ordered_features), dpi=dpi, 
           limitsize=False, verbose=False)
  return img_dir

def show_metadata_discrete_spatial_germLayer(adata, stage,  odir, embedding, obs=['celltype'], cmap = ctp_cmap, dpi=150, sort = False, ascending=True, **kws):
  embedding = embedding.loc[adata.obs_names,:]
  img_dir = '/rad/wuc/dash_data/spatial/tmp/%s/%s/poltFeatureSeries_%s_plot_dpi%d.png' % (odir, stage, obs, dpi)

  # if os.path.exists( img_dir ):
  #   return img_dir

  pdf = pd.DataFrame(np.array(embedding), 
                     index=adata.obs_names, 
                     columns=['x', 'y'])
  
  obs_df = pd.DataFrame(adata.obs[obs])

  pdf = pd.concat([pdf, obs_df, adata.obs.germ_layer], axis=1)
  pdf = pd.melt(pdf, id_vars = ['x', 'y', 'germ_layer'], var_name='obs', value_name='value')
  if sort:
    pdf = pdf.sort_values(by='value', ascending=ascending)
  pdf['obs'] = pdf['obs'].astype('category').values.reorder_categories(obs_df.columns)

  # plotnine
  (
    ggplot() + 
    geom_point(data = pdf, mapping=aes(x='x', y='y', color='value'), size=0.4) +
    facet_grid('obs ~ germ_layer') + 
    # scale_color_gradientn(colors = ['#e0e0e0', '#e0e0e0','#225ea8'], values = [0,0.05,1]) +
    scale_color_manual(values = ctp_cmap) +
    theme(
      # legend_position='top',
      # legend_direction='horizontal',
      axis_title = element_text(size=16),
      axis_text = element_text(size=10),
      panel_grid = element_blank(),
      panel_border = element_rect(linewidth=0.4, fill= 'None'),
      panel_background = element_rect(fill= 'None'),
      strip_text_x = element_text(size=16),
      strip_text_y = element_text(size=16, face = 'bold', angle=0)
    )
  ).save(img_dir, width=12, height=1+3*len(obs), dpi=dpi, 
         limitsize=False, verbose=False)
  return img_dir

def pre_SubsetCellsByObs(
  obs : pd.DataFrame, 
  germ_layers : List[str],
  celltypes : List[str],
  xyz_range : Dict,
  ):
  '''
  germ_layers: ectoderm, mesoderm, endoderm
  xy_range: dict(x=(minX, maxX),y=(minY, maxY))
  '''
  subset = obs.query(
    '(germ_layer in @germ_layers) & \
    (celltype in @celltypes) & \
    ( @xyz_range["x"][0] <= x <= @xyz_range["x"][1] ) & \
    ( @xyz_range["y"][0] <= y <= @xyz_range["y"][1] ) & \
    ( @xyz_range["z"][0] <= z <= @xyz_range["z"][1] )'
  )
  return subset.index

def show_expViolin(adata, feature, **kws):
  data = adata[:,feature].to_df()[feature]
  data = data[data>0]
  fig = go.Figure(
    data = go.Violin(
      x=data, y0=f'{feature}({len(data)})', box_visible=True, 
      line_color='black', meanline_visible=True,
      fillcolor='lightseagreen', opacity=0.6,
      pointpos = 1.5, jitter=0.2, **kws
    )
  )
  
  fig.update_traces(orientation='h', side='positive', points='all', marker_size=2.5)
  fig.update_layout(xaxis_showgrid=False, yaxis_showgrid=True)
  return fig

def show_ctpExpViolin(adata, feature, **kws):
  pdf = pd.concat([adata[:,feature].to_df(), adata.obs.celltype], axis=1)
  counts = pdf.celltype.value_counts()
  counts = counts[counts>0]
  sorted_ctp = counts.index.to_list()
  pdf['celltype'] = pd.Categorical(pdf['celltype'].to_list(),
                                   categories=sorted_ctp[::-1])
  fig = px.violin(
    pdf, x=feature, y='celltype', color = 'celltype', 
    color_discrete_map=ctp_cmap, orientation='h', height=800,
  ).update_traces(
    side='positive', width=1.5, jitter=0.2, marker_size=2.5
  ).update_layout(
    plot_bgcolor = 'rgba(200,200,200,0.1)',
  ).update_yaxes(
    gridcolor='rgba(200,200,200,0.6)', gridwidth=1,
  ).update_xaxes(
    dtick=1, gridcolor='#ffffff', gridwidth=1, griddash='solid'
  )
  return fig

def show_multiFeatures_expViolin(adata, features_dict, color_dict=None,**kws):
  if not color_dict:
    color_dict = {'R': 'tomato', 'G': 'springgreen', 'B': 'skyblue'}
  fig = go.Figure()
  
  tmp = {}
  for key,value  in features_dict.items():
      if value:
          tmp[key] = value
  features_dict = tmp

  for color,feature in features_dict.items():
    data = adata[:,feature].to_df()[feature]
    data = data[data>0]
    color = color_dict[color]
    fig.add_trace(
      go.Violin(
        x=data, y0=f'{feature}({len(data)})', box_visible=True, 
        line_color='black', meanline_visible=True,
        fillcolor=color, opacity=0.6,
        pointpos = 1.5, jitter=0.2, **kws
      )
    )
  fig.update_traces(orientation='h', side='positive', points=False, 
                    width=1.2)
  fig.update_layout(showlegend=False,xaxis_showgrid=False, yaxis_showgrid=True)
  return fig

def show_multiFeatures_ctpExpViolin(adata, features_dict, *kws):
  
  from plotly.subplots import make_subplots
  
  tmp = {}
  for key,value  in features_dict.items():
      if value:
          tmp[key] = value
  features_dict = tmp
  features = list(features_dict.values())
  ngenes = len(features_dict.keys())
  fig = make_subplots(1, ngenes)

  pdf = pd.concat([adata[:,features].to_df(), adata.obs.celltype], axis=1)
  pdf = pdf.melt(id_vars='celltype')
  pdf = pdf.rename(columns = {'variable': 'Gene', 'value': 'expression'})
  # pdf = pdf[pdf['expression']>0]

  pdf.celltype = pd.Categorical(pdf.celltype, ordered=True)
  # counts = pdf.groupby('Gene').apply(lambda x: x.value_counts())

  fig = px.violin(
    pdf, x='expression', y='celltype', color = 'celltype', 
    color_discrete_map=ctp_cmap, orientation='h', height=800,
    animation_frame='Gene', points='outliers'
  ).update_traces(
    side='positive', width=1.5, jitter=0.2, marker_size=2.5
  ).update_layout(
    plot_bgcolor = 'rgba(200,200,200,0.1)',
  ).update_yaxes(
    gridcolor='rgba(200,200,200,0.6)', gridwidth=1,
  ).update_xaxes(
    dtick=1, gridcolor='#ffffff', gridwidth=1, griddash='solid'
  )
    
  return fig

# In[] initial figure:
FIGURE_3Dexpression_initial = show_feature_spatial_3D(exp_data['E7.75'], 'Cdx1', coord_data['E7.75'][['x', 'y', 'z']])
FIGURE_3Dcelltype_initial = show_celltype_spatial_3D(exp_data['E7.75'], coord_data['E7.75'][['x', 'y', 'z']])

# In[] app/header:

app = Dash(
  __name__, 
  external_stylesheets=[
    dbc.themes.BOOTSTRAP,
    "/home/wuc/dashapps/css/dbc.min.css",
  ],
  external_scripts = [
    {'src': 'https://deno.land/x/corejs@v3.31.1/index.js', 'type': 'module'}
  ]
)


header = dbc.NavbarSimple(
    [
    #     dbc.DropdownMenu(
    #         children=[
    #             # dbc.DropdownMenuItem('spatial', href='/'),
    #             # dbc.DropdownMenuItem("atlas", href='/atlas'),
    #             # dbc.DropdownMenuItem("reik", href='/reik'),
    #         ],
    #         nav=True,
    #         in_navbar=True,
    #         label="Dataset",
    #     ),
    ],
    brand="Omics-viewer",
    color="dark",
    dark=True,
    sticky='top',
    style = {"height": "6vh"}
)

# In[] app/wdigets/flat :

spatial_dropdown_featureType = html.Div(
    [
        dbc.Label("Feature type"),
        dcc.Dropdown(
            ['Gene', 'Regulon'],
            'Gene',
            id="spatial_dropdown_featureType",
            clearable=False,
            searchable=True,
        ),
    ],
    className="mb-4",
)
spatial_dropdown_featureName = html.Div(
    [
        dbc.Label("Feature name"),
        dcc.Dropdown(
            exp_data['E7.75'].var_names,
            'Cdx1',
            id="spatial_dropdown_featureName",
            clearable=True,
            searchable=True,
        ),
    ],
    className="mb-4",
)
spatial_dropdown_stage = html.Div(
    [
        dbc.Label("Stage"),
        dcc.Dropdown(
            ['E7.5', 'E7.75', 'E8.0'],
            'E7.75',
            id="spatial_dropdown_stage",
            clearable=False,
            searchable=True,
        ),
    ],
    className="mb-4",
)


# In[] app/widgets/3D:

CHECKLIST_germLayer_3D = html.Div(
    [
        # dbc.Label("Germ layers to show:"),
        dbc.Checklist(
            options=[
                {"label": " Ectoderm", "value": 'ectoderm'},
                {"label": " Mesoderm", "value": 'mesoderm'},
                {"label": " Endoderm", "value": 'endoderm'},
            ],
            value=['ectoderm', 'mesoderm', 'endoderm'],
            id="CHECKLIST_germLayer_3D",
            switch=True
        ),
    ],
    className="mb-4",
)

SWITCH_hideZero_3D = html.Div([
  dbc.Row(
    [
        dbc.Col(
            dbc.Label("Hide zero:"),
            width=6
            ),
        dbc.Col(
            daq.BooleanSwitch(id='SWITCH_hideZero_3D', on=False),
            width=4
            )
    ]
  )
])

SWITCH_hideAxes_3D = html.Div([
  dbc.Row(
    [
      dbc.Col(
        dbc.Label('Hide axes:'),
        width=6,
      ),
      dbc.Col(
        daq.BooleanSwitch(on=False, id='SWITCH_hideAxes_3D'),
        width=4
      )
    ]
  )
])

SET_topViewer_controler_3D = html.Div([
  dbc.Row(
    [
      dbc.Col([
        dbc.Label('x range'),
        dcc.RangeSlider(-400,480,10, value=(-400,480), id='Slider_Xrange_3D',
                        marks=None,tooltip={'placement': 'bottom', 'always_visible': True})
      ], width=2),
      dbc.Col([
        dbc.Label('y range'),
        dcc.RangeSlider(-410, 470,10, value=(-410,470), id='Slider_Yrange_3D',
                        marks=None,tooltip={'placement': 'bottom', 'always_visible': True})
      ], width=2),
      dbc.Col([
        dbc.Label('z range'),
        dcc.RangeSlider(0, 700,10, value=(0,700), id='Slider_Zrange_3D',
                        marks=None,tooltip={'placement': 'bottom', 'always_visible': True})
      ], width=2),
      dbc.Col([
        dbc.Row([
          dbc.Col(dbc.Label('Preview'), width=4),
          dbc.Col(daq.BooleanSwitch(on=False, id='SWITCH_previewBox_3D'),width=4)
        ]),
        dbc.Row([
          dbc.Col(dbc.Button('Slice', color='danger', id='BUTTON_slice_3D'),width=4),
          dbc.Col(dbc.Button('Recover', color='success', id='BUTTON_recover_3D'),width=4),
        ])
      ], width=2),
      dbc.Col([
        CHECKLIST_germLayer_3D
      ], width=2),
      dbc.Col([
        SWITCH_hideZero_3D,
        SWITCH_hideAxes_3D
      ], width=2)
    ],
    style = {'height': '8vh'}
  ),
  dcc.Store(id='STORE_previewRange_3D'),
  dcc.Store(id='STORE_sliceRange_3D'),
  dcc.Store(id='STORE_maxRange_3D'),
], className='mb-4')

SET_STORE_JSONtoPlot = html.Div(
  [
    dcc.Store
  ]
)

# In[] app/widgets/series:

spatial_dropdown_featureType_series = html.Div(
    [
        dbc.Label("Feature type"),
        dcc.Dropdown(
            ['Gene'],
            'Gene',
            id="spatial_dropdown_featureType_series",
            clearable=False,
            searchable=True,
        ),
    ],
    className="mb-4",
)
spatial_input_featureName_series = html.Div(
    [
        dbc.Label("Starts with"),
        dbc.InputGroup(
          [
            dbc.Input(id="spatial_input_featureName_series"),
            dbc.Button('Plot', id='spatial_inputButton_featureName_series_plot',
                                n_clicks=0, color='primary'),
          ]
        )
    ],
    className="mb-4",
)
spatial_textarea_featureLists_series = html.Div(
  [
    dbc.Label("name list:"),
    dbc.Col(
      [
        dbc.Textarea(id = "spatial_textarea_featureLists_series",
          placeholder="paste feature names here(seperated by any charactor)\ne.g.  A  B,C,  D\nE##F--G_H,#I@KK%%G%(U),(V)|(W)\"X\",\"Y\"^Q*I",
          rows=8, className="mb-3",),
        dbc.Button('Plot', id='spatial_inputButton_featureLists_series_plot',
                          n_clicks=0, color='primary'),
      ]
    )
  ],
  className="mb-4",
)
spatial_dropdown_stage_series = html.Div(
    [
        dbc.Label("Stage"),
        dcc.Dropdown(
            ['E7.5', 'E7.75', 'E8.0'],
            'E7.75',
            id="spatial_dropdown_stage_series",
            clearable=False,
            searchable=True,
        ),
    ],
    className="mb-4",
)


# ### tabs
# In[] app/tabs/:

spatial_tab_plotFeature = dbc.Tab(
  [dbc.Row([
    dbc.Col([
      dbc.Card(
        [
          spatial_dropdown_featureType,
          spatial_dropdown_featureName,
          # spatial_dropdown_plotDim,
          spatial_dropdown_stage
        ],
        body=True,
        id = 'spatial_control_plotFeature'
      ),      
    ], width=2),
    dbc.Col([dbc.Row([
      dbc.Col([
        dcc.Graph(figure={}, id="spatial_plotFeature_graph", style={'height': "40vh"}),
      ],align = "center",className="g-0", width=12),
      dbc.Col([
        dcc.Graph(figure={}, id="spatial_plotFeature_graph_ctp", style={'height': "40vh"}),
      ],align = "center",className="g-0", width=12)
    ]),],width=10),
  ])],
  label = "Plot feature(flat)",
  tab_id = "spatial_tab_plotFeature"
)

spatial_tab_plotFeature3D = dbc.Tab(
  [dbc.Row([
    dbc.Col([
      html.Div([
        # Basic options
        dbc.Card(
          [
            dbc.CardHeader('Basic options:'),
            dbc.CardBody([
              dbc.Row([
                dbc.Col([
                  dbc.Label("Feature type"),
                  dcc.Dropdown(
                      ['Gene', 'Regulon'],
                      'Gene',
                      id="DROPDOWN_featureType_3D",
                      clearable=False,
                      searchable=True,
                  ),
                ], width=6),
                dbc.Col([
                  dbc.Label("Stage"),
                  dcc.Dropdown(
                      ['E7.5', 'E7.75', 'E8.0'],
                      'E7.75',
                      id="DROPDOWN_stage_3D",
                      clearable=False,
                      searchable=True,
                  ),
                ], width=6),
              ]),
            ])
          ],
        ),
        # Single gene
        dbc.Card(
          [
            dbc.CardHeader([
              dbc.Row([
                dbc.Col(html.Div('Plot single features:'), width=9),
                # dbc.Col(dbc.Switch(value=True, id='if_plotSingleFeature_3D'), width=3)
              ]),
            ]),
            dbc.CardBody([
              dbc.Row(
                [
                  dbc.Col([
                    dcc.Dropdown(
                      options = exp_data['E7.75'].var_names,
                      value = 'Cdx1',
                      id="DROPDOWN_singleName_3D",
                      clearable=False
                    ),
                  ], width=8),
                  dbc.Col([
                    dbc.Button('Plot', id='BUTTON_singlePlot_3D', n_clicks=0, color='dark', disabled=False),
                  ], width=4),
                ],className="mb-4",
              )
            ])
          ],
        ),
        # Multi genes
        dbc.Card(
          [
            dbc.CardHeader([
              dbc.Row([
                dbc.Col(html.Div('Plot multi features:'), width=9),
                # dbc.Col(dbc.Switch(value=False, id='if_plotMultiFeature_3D'), width=3),
              ])
            ]),
            dbc.CardBody([
              dbc.Col([
                dbc.Row([
                  dbc.Col(dcc.Dropdown(options = exp_data['E7.75'].var_names,
                                      id='DROPDOWN_multiNameR_3D'),
                          width=10),
                  dbc.Col(dbc.Badge("R", color='danger'),width=2),
                ]),
                dbc.Row([
                  dbc.Col(dcc.Dropdown(options = exp_data['E7.75'].var_names,
                                      id='DROPDOWN_multiNameG_3D'), 
                          width=10),
                  dbc.Col(dbc.Badge("G", color='success'),width=2),
                ]),
                dbc.Row([
                  dbc.Col(dcc.Dropdown(options = exp_data['E7.75'].var_names,
                                      id='DROPDOWN_multiNameB_3D'), 
                          width=10),
                  dbc.Col(dbc.Badge("B", color='primary'),width=2),
                ]),
                dbc.Row([
                  dbc.Button('Plot', id='BUTTON_multiPlot_3D', n_clicks=0, color='dark', disabled=False),
                ], justify='center'),
                dcc.Store(id='STORE_multiNameInfo_3D')
              ],)
            ])
          ],
        ),
        # Moran
        dbc.Card(
          [
            dbc.CardHeader([
              'Moran',
            ]),
            dbc.CardBody([
              dbc.Button('calculate SVGs', id='cal_moranSVG', color='black', disabled=False),
              dag.AgGrid(id='res_moranSVG'),
            ]),
          ]
        )
      ], style = {'position':'fixed', 'width':'30vh'}),
    ], width=2),
    dbc.Col([
      SET_topViewer_controler_3D,
      dcc.Store(id='STORE_JSONtoPlot_3D'),
      dbc.Row([
        dbc.Col([
          dcc.Graph(figure=FIGURE_3Dexpression_initial, id="FIGURE_3Dexpression", 
                    style={'height': "75vh"}, ),
        ],align = "center", width=5),
        dbc.Col([
          dcc.Graph(figure=FIGURE_3Dcelltype_initial, id="FIGURE_3Dcelltype", 
                    style={'height': "75vh"}),
        ],align = "center", width=7)
      ]),
      dbc.Row([
        dbc.Col([
          dbc.Label( 'Normalized expression(non-zero) in all celltypes(left)'),
          dbc.Label('and in each celltype(right):'),
          dcc.Graph(figure={}, id="FIGURE_expViolin_3D"),
        ], align='center', width=5),
        dbc.Col([
          dcc.Graph(figure={}, id="FIGURE_ctpViolin_3D"),
        ], align='center', width=7)
      ])
    ],width=10),
  ]), html.Div(id='test')],
  label = "Plot feature(3D)",
  tab_id = "spatial_tab_plotFeature3D",
)

spatial_tab_plotFeatureSeries = dbc.Tab(
  [dbc.Row([
    dbc.Col([
      dbc.Card(
        [
          dbc.Col([
            spatial_dropdown_featureType_series,
            spatial_dropdown_stage_series,
            spatial_input_featureName_series,
            spatial_textarea_featureLists_series,
          ])
        ],
        body=True,
        style = {'position': 'fixed'},
        id = 'spatial_control_plotFeatureSeries'
      )
    ], width=2),
    dbc.Col([
      dbc.Row(
        [
          dbc.Col(width=2),
          dbc.Col([
            dcc.Graph(figure={}, id="spatial_plotFeatureSeries_graph_ctp", style={'height': "50vh"}),
          ],align = "center",className="g-0", width=8),
        ]
      ),
      dbc.Row([
        dbc.Col(
          [
            html.Img(
              # src = Image.open('/rad/wuc/dash_data/spatial/tmp/plotFeatureSeries/E7.75/plotFeatureSeries_E7.75_^Cdx_Gene_dpi100.png'),
                     id = 'spatial_plotFeatureSeries_img', style = {'width': '90vh'})
          ],
          align = "center", className="g-0", width=7),
        dbc.Col(
          [
            html.Img(
              # src = Image.open('/rad/wuc/dash_data/spatial/tmp/plotFeatureSeries/E7.75/plotFeatureSeries_E7.75_ctpCounts_^Cdx_Gene_dpi150.png'),
                     id = 'spatial_plotFeatureSeries_ctpCounts_img', style = {'width': '60vh'})
          ],
          
          align = "center", className="g-0", width=5)
      ],),
    ], width=10)
  ])],
  label = "Plot feature(Series)",
  tab_id = "spatial_tab_plotFeatureSeries"
)

spatial_tab_plotFeatureSparkx = dbc.Tab(
  [
    dcc.Store(
      id='clientside_store_table_sparkx'
    ),
    dbc.Row([
      dbc.Col([
        html.Div(
          dbc.Row([
            dbc.Col([
              dbc.Label("Feature type"),
              dcc.Dropdown(['Gene'], 'Gene', id='spatial_dropdown_featureType_sparkx', clearable=False)
            ], width=4),
            dbc.Col([
              dbc.Label("Stage"),
              dcc.Dropdown(['E7.5', 'E7.75', 'E8.0'],'E7.75', id='spatial_dropdown_stage_sparkx', clearable=False)
            ], width=4),
            dbc.Col([
              dbc.Label("Genes per page"),
              dcc.Dropdown([10, 15, 20, 30, 50, 100], 15, id='spatial_dropdown_pageSize_sparkx', clearable=False)
            ], width=4)
          ])
        ),
        dash_table.DataTable(id = "spatial_dataTable_sparkx",
          row_selectable = 'single', sort_action="native", page_action='native',
          filter_action="native", page_current= 0, page_size= 15,fill_width=True, 
          style_table={'overflowX': 'auto'},
          style_cell={'padding-right': '10px', 'padding-left': '10px',
            'text-align': 'center', 'marginLeft': 'auto', 'marginRight': 'auto' }
        ),
      ], width=4),
      dbc.Col([
        dbc.Col([
          dcc.Graph(figure={}, id="spatial_featureGraph_sparkx", style={'height': "36vh", 'width': '130vh'}),
          dcc.Graph(figure={}, id="spatial_celltypeGraph_sparkx", style={'height': "36vh", 'width': '130vh'}),
        ], style = {'position': 'fixed'}),
      ],width=8)
    ]),
  ],
  label = "SPARK-X",
  tab_id = "spatial_tab_plotFeatureSparkx"
)

spatial_tabs = dbc.Card(
    dbc.Tabs(
        [spatial_tab_plotFeature, spatial_tab_plotFeature3D, spatial_tab_plotFeatureSeries, spatial_tab_plotFeatureSparkx],
        active_tab = "spatial_tab_plotFeature",  
        id = "spatial_tabs",
    ),
)


# In[] callbacks/flat :

@app.callback(
  Output('spatial_dropdown_featureName', 'options'),
  Input('spatial_dropdown_featureName', 'search_value'),
  Input('spatial_dropdown_featureType', 'value'),
  Input('spatial_dropdown_stage', 'value')
)
def update_spatial_dropdown_featureName(search, featureType, stage):
  if not search:
    raise PreventUpdate
  
  if featureType == 'Gene':
    if not search:
      return exp_data[stage].var_names
    else:
      return exp_data[stage].var_names[exp_data[stage].var_names.str.startswith(search)].sort_values()
  elif featureType == 'Regulon':
    if not search:
      return auc_data[stage].var_names
    else:
      return auc_data[stage].var_names[auc_data[stage].var_names.str.startswith(search)].sort_values()

@app.callback(
  Output('spatial_plotFeature_graph', 'figure'),
  State('spatial_dropdown_featureType', 'value'),
  Input('spatial_dropdown_featureName', 'value'),
  Input('spatial_dropdown_stage', 'value'),
  # background=True,
  # manager=background_callback_manager,
)
def update_spatial_plotFeature_graph(featureType, name, stage):
  if name is None:
    raise PreventUpdate
  
  if featureType == 'Gene':
      adata = exp_data[stage]
  elif featureType == 'Regulon':
      adata = auc_data[stage]
  else:
    raise PreventUpdate

  return show_feature_spatial(adata, name, embedding = coord_data[stage][['x_flatten', 'y_flatten']], sort=True, ascending=True,
                            facet_col = 'germ_layer', category_orders={'germ_layer':['ectoderm','mesoderm','endoderm']})

@app.callback(
  Output('spatial_plotFeature_graph_ctp', 'figure'),
  State('spatial_dropdown_featureType', 'value'),
  Input('spatial_dropdown_stage', 'value'),
  background=True,
  manager=background_callback_manager,
)
def update_spatial_plotFeature_ctpGraph(featureType, stage):

  if featureType == 'Gene':
      adata = exp_data[stage]
  elif featureType == 'Regulon':
      adata = auc_data[stage]
  else:
    raise PreventUpdate

  return show_celltype_spatial(adata, embedding = coord_data[stage][['x_flatten', 'y_flatten']],
                               facet_col = 'germ_layer', 
                               category_orders={'germ_layer':['ectoderm','mesoderm','endoderm']})


# In[] callbacks/3D :


# update_nameOptions
@app.callback(
  Output('DROPDOWN_singleName_3D', 'options'),
  Input('DROPDOWN_singleName_3D', 'search_value'),
  Input('DROPDOWN_featureType_3D', 'value'),
  Input('DROPDOWN_stage_3D', 'value')
)
def update_nameOptions_single_3D(search, featureType, stage):
  if not search:
    raise PreventUpdate
  
  if featureType == 'Gene':
    if not search:
      opts = exp_data[stage].var_names
    else:
      opts = exp_data[stage].var_names[exp_data[stage].var_names.str.startswith(search)].sort_values()
  elif featureType == 'Regulon':
    if not search:
      opts = auc_data[stage].var_names
    else:
      opts = auc_data[stage].var_names[auc_data[stage].var_names.str.startswith(search)].sort_values()
  
  return opts

@app.callback(
  Output('DROPDOWN_multiNameR_3D', 'options'),
  Input('DROPDOWN_multiNameR_3D', 'search_value'),
  Input('DROPDOWN_featureType_3D', 'value'),
  Input('DROPDOWN_stage_3D', 'value')
)
def update_nameOptions_multiR_3D(search, featureType, stage):
  if not search:
    raise PreventUpdate
  
  if featureType == 'Gene':
    if not search:
      opts = exp_data[stage].var_names
    else:
      opts = exp_data[stage].var_names[exp_data[stage].var_names.str.startswith(search)].sort_values()
  elif featureType == 'Regulon':
    if not search:
      opts = auc_data[stage].var_names
    else:
      opts = auc_data[stage].var_names[auc_data[stage].var_names.str.startswith(search)].sort_values()
  
  return opts

@app.callback(
  Output('DROPDOWN_multiNameG_3D', 'options'),
  Input('DROPDOWN_multiNameG_3D', 'search_value'),
  Input('DROPDOWN_featureType_3D', 'value'),
  Input('DROPDOWN_stage_3D', 'value')
)
def update_nameOptions_multiG_3D(search, featureType, stage):
  if not search:
    raise PreventUpdate
  
  if featureType == 'Gene':
    if not search:
      opts = exp_data[stage].var_names
    else:
      opts = exp_data[stage].var_names[exp_data[stage].var_names.str.startswith(search)].sort_values()
  elif featureType == 'Regulon':
    if not search:
      opts = auc_data[stage].var_names
    else:
      opts = auc_data[stage].var_names[auc_data[stage].var_names.str.startswith(search)].sort_values()
  
  return opts

@app.callback(
  Output('DROPDOWN_multiNameB_3D', 'options'),
  Input('DROPDOWN_multiNameB_3D', 'search_value'),
  Input('DROPDOWN_featureType_3D', 'value'),
  Input('DROPDOWN_stage_3D', 'value')
)
def update_nameOptions_multiB_3D(search, featureType, stage):
  if not search:
    raise PreventUpdate
  
  if featureType == 'Gene':
    if not search:
      opts = exp_data[stage].var_names
    else:
      opts = exp_data[stage].var_names[exp_data[stage].var_names.str.startswith(search)].sort_values()
  elif featureType == 'Regulon':
    if not search:
      opts = auc_data[stage].var_names
    else:
      opts = auc_data[stage].var_names[auc_data[stage].var_names.str.startswith(search)].sort_values()
  
  return opts


# store_multiNameInfo
app.clientside_callback(
  '''
  function(R,G,B){
    var dict = {'R': R, 'G': G, 'B': B}
    return dict
  }
  ''',
  Output('STORE_multiNameInfo_3D', 'data'),
  Input('DROPDOWN_multiNameR_3D', 'value'),
  Input('DROPDOWN_multiNameG_3D', 'value'),
  Input('DROPDOWN_multiNameB_3D', 'value'),
)


# store_expForJSONtoPlot
@app.callback(
  Output('STORE_JSONtoPlot_3D', 'data'),
 
  Input('BUTTON_singlePlot_3D', 'n_clicks'),
  State('DROPDOWN_singleName_3D', 'value'),
 
  Input('BUTTON_multiPlot_3D', 'n_clicks'),
  State('STORE_multiNameInfo_3D', 'data'),
 
  Input('DROPDOWN_stage_3D', 'value'),
  Input('DROPDOWN_featureType_3D', 'value'),
  
  Input('SWITCH_hideZero_3D', 'on'),
)
def store_expForJSONtoPlot_3D(sclick, sname, mclick, minfo, stage, featureType, hideZero):
  patch = Patch()
  
  if featureType == 'Gene':
    adata = exp_data[stage]
  elif featureType == 'Regulon':
    adata = auc_data[stage]
  else:
    raise PreventUpdate
  
  triggered = ctx.triggered_id
  
  if triggered and 'BUTTON_singlePlot' in triggered:
    
    patch['ifmulti'] = False
    exp = adata[:,sname].X.toarray().reshape(-1)
    patch['singleExp'] = exp
    if hideZero:
      patch['cellsExpFilter'] = exp>0

  elif triggered and 'BUTTON_multiPlot' in triggered:
    
    patch['ifmulti'] = True
    exp = {}
    for c,name in minfo.items():
      exp[name] = adata[:,name].X.toarray().reshape(-1)
    patch['multiExp'] = exp
    if hideZero:
      ifNoZero = pd.DataFrame(exp)
      patch['cellsExpFilter'] = ~ifNoZero.apply(any, axis=1)

  return patch


# store_previewRange
app.clientside_callback(
  '''
  function(x_range, y_range, z_range){
    var dict = {'x_min': x_range[0], 'x_max': x_range[1],
                'y_min': y_range[0], 'y_max': y_range[1],
                'z_min': z_range[0], 'z_max': z_range[1]}
    return dict                
  }
  ''',
  Output('STORE_previewRange_3D', 'data'),
  Input('SLIDER_Xrange_3D', 'value'),
  Input('SLIDER_Yrange_3D', 'value'),
  Input('SLIDER_Zrange_3D', 'value'),
)

# store_maxRange
app.clientside_callback(
  '''
  function(plotData){
    var minx = Math.min(plotData['obs']['x'])
    var maxx = Math.max(plotData['obs']['x'])
    var miny = Math.min(plotData['obs']['y'])
    var maxy = Math.max(plotData['obs']['y'])
    var minz = Math.min(plotData['obs']['z'])
    var maxz = Math.max(plotData['obs']['z'])
    var dict = {'x_min': minx, 'x_max': maxx,
                'y_min': miny, 'y_max': maxy,
                'z_min': minz, 'z_max': maxz}
    return dict
  }
  ''',
  Output('STORE_maxRange_3D', 'data'),
  Input('STORE_JSONtoPlot_3D', 'data'),
)

# store_sliceRange
app.clientside_callback(
  '''
  function(slice, recover, previewRange, maxRange){
    const id = dash_clientside.callback_context.triggered.map(t => t.prop_id)
    if(id == 'BUTTON_slice_3D'){
      return previewRange
    } else {
      return maxRange
    }
  }
  ''',
  Output('STORE_sliceRange_3D', 'data'),
  Input('BUTTON_slice_3D', 'n_clicks'),
  Input('BUTTON_recover_3D', 'n_clicks'),
  State('STORE_previewRange_3D', 'data'),
  State('STORE_maxRange_3D', 'data'),
)

# store_cellsInfo_forJSONtoPlot
@app.callback(
  Output('STORE_JSONtoPlot_3D', 'data'),
  
  Input('STORE_sliceRange_3D', 'data'),
  Input('CHECKLIST_germLayer_3D', 'value'),
  Input('DROPDOWN_stage_3D', 'value'),
  Input('DROPDOWN_featureType_3D', 'value'),
)
def store_cellsInfo_forJSONtoPlot_3D(sliceRange, germs, stage, featureType):

  if featureType == 'Gene':
    adata = exp_data[stage]
  elif featureType == 'Regulon':
    adata = auc_data[stage]
  else:
    raise PreventUpdate

  obs = adata.obs[['x','y','z','germ_layer','celltype']]

  if_inSliceRange = ( 
                      (obs['x'] <= sliceRange['x_max']) & 
                      (obs['x'] >= sliceRange['x_min']) & 
                      (obs['y'] <= sliceRange['y_max']) & 
                      (obs['y'] >= sliceRange['y_min']) & 
                      (obs['z'] <= sliceRange['z_max']) & 
                      (obs['z'] >= sliceRange['z_min'])
                    )
  
  if len(germs) > 1:
    if_ingerms = [ True if i in germs else False for i in obs['germ_layer'] ]
  else:
    raise PreventUpdate

  obs_filter = adata.obs_names[if_inSliceRange & if_ingerms]

  patch = Patch()
  patch['obs'] = obs.to_dict('index')
  patch['cellsObsFilter'] = obs_filter
  
  return patch


# plot_3Dexpression
app.clientside_callback(
  '''
  function(data){
    var obs = data['obs']
    var obsFilter = data['cellsObsFilter']
    var expFilter = data['cellsExpFilter']
    var ifmulti = data['ifmulti']
    var singleExp = data['singleExp']
    var multiExp = data['multiExp']
    
  }
  ''',
  Output('FIGURE_3Dexpression', 'figure'),
  Input('STORE_JSONtoPlot_3D', 'data'),
  State('FIGURE_3Dexpression', 'figure')
)
  



@app.callback(
  Input('STORE_JSONtoPlot_3D', 'data'),
  Output('FIGURE_3Dcelltype', 'figure')
)
def plot_3Dcelltype():

  return



####################################################
@app.callback(
  Output('FIGURE_3Dexpression', 'figure'),
  
  State('DROPDOWN_featureType_3D', 'value'),
  State('DROPDOWN_singleName_3D', 'value'),
  Input('BUTTON_singlePlot_3D', 'n_clicks'),
  Input('DROPDOWN_stage_3D', 'value'),
  Input('CHECKLIST_germLayer_3D', 'value'),
  Input('SWITCH_hideZero_3D', 'on'),
  State('SWITCH_hideAxes_3D', 'on'),
  Input('BUTTON_slice_3D', 'n_clicks'),
  Input('BUTTON_recover_3D', 'n_clicks'),
  State('STORE_previewRange_3D', 'data'),
  Input('BUTTON_multiPlot_3D', 'n_clicks'),
  State('STORE_multiNameInfo_3D', 'data'),
  State('if_plotMultiFeature_3D', 'value'),
)
def update_FIGURE_3Dexpression(featureType, name, splot, stage, germs, hideZero, hideAxis,
                                      slice,recover,range, mplot, mgenes_info, ifmulti):
  if name is None:
    raise PreventUpdate
  
  if featureType == 'Gene':
      adata = exp_data[stage]
  elif featureType == 'Regulon':
      adata = auc_data[stage]

  adata = adata[[i in germs for i in adata.obs.germ_layer]]

  if hideZero:
    adata = adata[adata[:,name].X!=0]
  
  if ctx.triggered_id and 'BUTTON_slice_3D' in ctx.triggered_id:
    print('slice',ctx.triggered_id)
    adata = adata[(adata.obs.x >= range['x_min']) & 
                  (adata.obs.x <= range['x_max']) & 
                  (adata.obs.y >= range['y_min']) & 
                  (adata.obs.y <= range['y_max']) & 
                  (adata.obs.z >= range['z_min']) & 
                  (adata.obs.z <= range['z_max'])]

  if ifmulti:
    fig = show_multiFeatures_spatial_3D(adata, mgenes_info, embedding = coord_data[stage].loc[:,['x', 'y', 'z']])
  else:
    fig = show_feature_spatial_3D(adata,name, embedding = coord_data[stage].loc[:,['x', 'y', 'z']], sort=True, ascending=True)

  if hideAxis:
    fig.update_layout(
      scene = dict(
        xaxis={'visible': False},
        yaxis={'visible': False},
        zaxis={'visible': False},
      )
    )

  return fig

@app.callback(
  Output('STORE_multiNameInfo_3D', 'data'),
  Input('DROPDOWN_multiNameR_3D', 'value'),
  Input('DROPDOWN_multiNameG_3D', 'value'),
  Input('DROPDOWN_multiNameB_3D', 'value')
)  
def store_multiNamesInfo(geneR,geneG,geneB):
  genes_dict = {
    'R': geneR, 'G': geneG, 'B': geneB
  }
  return genes_dict
  
@app.callback(
  Output('FIGURE_3Dcelltype', 'figure'),
  State('DROPDOWN_featureType_3D', 'value'),
  State('DROPDOWN_singleName_3D', 'value'),
  Input('DROPDOWN_stage_3D', 'value'),
  Input('CHECKLIST_germLayer_3D', 'value'),
  Input('SWITCH_hideZero_3D', 'on'),
  State('SWITCH_hideAxes_3D', 'on'),
  Input('BUTTON_slice_3D', 'n_clicks'),
  Input('BUTTON_recover_3D', 'n_clicks'),
  State('STORE_previewRange_3D', 'data'),
  # background=True,
  # manager=background_callback_manager,
)
def update_spatial_plotFeature3D_ctpGraph(featureType, name, stage, germs, hideZero, hideAxis,
                                          slice,recover,range):

  if featureType == 'Gene':
      adata = exp_data[stage]
  elif featureType == 'Regulon':
      adata = auc_data[stage]

  adata = adata[[i in germs for i in adata.obs.germ_layer]]
  
  if hideZero:
    adata = adata[adata[:,name].X!=0]
  
  if ctx.triggered_id and 'BUTTON_slice_3D' in ctx.triggered_id:
    adata = adata[(adata.obs.x >= range['x_min']) & 
                  (adata.obs.x <= range['x_max']) & 
                  (adata.obs.y >= range['y_min']) & 
                  (adata.obs.y <= range['y_max']) & 
                  (adata.obs.z >= range['z_min']) & 
                  (adata.obs.z <= range['z_max'])]

  fig = show_celltype_spatial_3D(adata, embedding = coord_data[stage][['x', 'y', 'z']])
  
  if hideAxis:
    fig.update_layout(
      scene = dict(
        xaxis={'visible': False},
        yaxis={'visible': False},
        zaxis={'visible': False},
      )
    )
  return fig
 
@app.callback(
    Output("FIGURE_3Dcelltype", "figure", allow_duplicate=True),
    Input("FIGURE_3Dexpression", "relayoutData"),
    prevent_initial_call=True
)
def update_relayout(data):   
    if data and 'scene.camera' in data:
        patch = Patch()
        patch['layout']['scene']['camera'] = data['scene.camera']
        return patch
    else:
        raise PreventUpdate
    
@app.callback(
    Output("FIGURE_3Dexpression", "figure", allow_duplicate=True),
    
    Input("FIGURE_3Dcelltype", "restyleData"),
    State("FIGURE_3Dcelltype", "figure"),
    State('DROPDOWN_featureType_3D', 'value'),
    State('DROPDOWN_singleName_3D', 'value'),
    State('DROPDOWN_stage_3D', 'value'),
    State('CHECKLIST_germLayer_3D', 'value'),
    State('SWITCH_hideZero_3D', 'on'),
    State('SWITCH_hideAxes_3D', 'on'),
    State('BUTTON_slice_3D', 'n_clicks'),
    State('BUTTON_recover_3D', 'n_clicks'),
    State('STORE_previewRange_3D', 'data'),
    State('STORE_multiNameInfo_3D', 'data'),
    State('if_plotMultiFeature_3D', 'value'),
    prevent_initial_call=True,
)
def update_restyle_legendClicking(restyle, fig, featureType, name, stage, germs, hideZero, hideAxis,
                                      slice,recover,range, mgenes_info, ifmulti):
  show_ctps = [ i['name'] for i in fig['data'] if (
                (i['type']!='mesh3d') and 
                ('visible' not in i or i['visible'] == True) 
              )]
  if featureType == 'Gene':
      adata = exp_data[stage]
  elif featureType == 'Regulon':
      adata = auc_data[stage]

  adata = adata[[(adata.obs.loc[i,'germ_layer'] in germs and 
                  adata.obs.loc[i,'celltype'] in show_ctps) 
                  for i in adata.obs_names]]
  if hideZero:
    adata = adata[adata[:,name].X!=0]
  
  if ctx.triggered_id and 'BUTTON_slice_3D' in ctx.triggered_id:
    print('slice',ctx.triggered_id)
    adata = adata[(adata.obs.x >= range['x_min']) & 
                  (adata.obs.x <= range['x_max']) & 
                  (adata.obs.y >= range['y_min']) & 
                  (adata.obs.y <= range['y_max']) & 
                  (adata.obs.z >= range['z_min']) & 
                  (adata.obs.z <= range['z_max'])]
      
  if ifmulti:
    fig = show_multiFeatures_spatial_3D(adata, mgenes_info, embedding = coord_data[stage].loc[:,['x', 'y', 'z']])
  else:
    fig = show_feature_spatial_3D(adata,name, embedding = coord_data[stage].loc[:,['x', 'y', 'z']], sort=True, ascending=True)
 
  if hideAxis:
    fig.update_layout(
      scene = dict(
        xaxis={'visible': False},
        yaxis={'visible': False},
        zaxis={'visible': False},
      )
    )

  return fig

@app.callback(
  Output('FIGURE_expViolin_3D', 'figure'),
  State('DROPDOWN_featureType_3D', 'value'),
  Input('DROPDOWN_singleName_3D', 'value'),
  Input('DROPDOWN_stage_3D', 'value'),
  Input('BUTTON_slice_3D', 'n_clicks'),
  Input('BUTTON_recover_3D', 'n_clicks'),
  State('STORE_previewRange_3D', 'data'),
  Input('BUTTON_multiPlot_3D', 'n_clicks'),
  State('STORE_multiNameInfo_3D', 'data')
)
def update_FIGURE_expViolin_3D(featureType, name, stage, slice, recover, range, mplot, mgenes_info):
  if name is None:
    raise PreventUpdate
  
  if featureType == 'Gene':
      adata = exp_data[stage]
  elif featureType == 'Regulon':
      adata = auc_data[stage]
  else:
    raise PreventUpdate

  triggered =ctx.triggered_id
  if triggered and 'BUTTON_slice_3D' in triggered:
    adata = adata[(adata.obs.x >= range['x_min']) & 
                  (adata.obs.x <= range['x_max']) & 
                  (adata.obs.y >= range['y_min']) & 
                  (adata.obs.y <= range['y_max']) & 
                  (adata.obs.z >= range['z_min']) & 
                  (adata.obs.z <= range['z_max'])]

  if ctx.triggered_id and 'BUTTON_multiPlot_3D' in ctx.triggered_id and mplot:
    fig = show_multiFeatures_expViolin(adata, mgenes_info)
  else:
    fig = show_expViolin(adata,name)

  return fig

@app.callback(
  Output('FIGURE_ctpViolin_3D', 'figure'),
  State('DROPDOWN_featureType_3D', 'value'),
  Input('DROPDOWN_singleName_3D', 'value'),
  Input('DROPDOWN_stage_3D', 'value'),
  Input('BUTTON_slice_3D', 'n_clicks'),
  Input('BUTTON_recover_3D', 'n_clicks'),
  State('STORE_previewRange_3D', 'data'),
  Input('BUTTON_multiPlot_3D', 'n_clicks'),
  State('STORE_multiNameInfo_3D', 'data')
)
def update_FIGURE_ctpViolin_3D(featureType, name, stage,  slice, recover, range, mplot, mgenes_info):
  if name is None:
    raise PreventUpdate
  
  if featureType == 'Gene':
      adata = exp_data[stage]
  elif featureType == 'Regulon':
      adata = auc_data[stage]
  else:
    raise PreventUpdate

  triggered = ctx.triggered_id
  if triggered and 'BUTTON_slice_3D' in triggered:
    adata = adata[(adata.obs.x >= range['x_min']) & 
                  
                  (adata.obs.x <= range['x_max']) & 
                  (adata.obs.y >= range['y_min']) & 
                  (adata.obs.y <= range['y_max']) & 
                  (adata.obs.z >= range['z_min']) & 
                  (adata.obs.z <= range['z_max'])]

  if ctx.triggered_id and 'BUTTON_multiPlot_3D' in ctx.triggered_id and mplot:
    fig = show_multiFeatures_ctpExpViolin(adata, mgenes_info)
  else:
    fig = show_ctpExpViolin(adata,name)
    
  return fig

# cal moran
@app.callback(
  Output('res_moranSVG', 'cildren'),
  Input('cal_moranSVG', 'n_clicks'),
  State('DROPDOWN_featureType_3D', 'value'),
  State('DROPDOWN_singleName_3D', 'value'),
  State('DROPDOWN_stage_3D', 'value'),
  State('CHECKLIST_germLayer_3D', 'value'),
  State('STORE_previewRange_3D', 'data'),
)
def display_moranRes3D():
  
  return

# Hide axies
@app.callback(
  Output('FIGURE_3Dexpression', 'figure', allow_duplicate=True),
  Output('FIGURE_3Dcelltype', 'figure', allow_duplicate=True),
  Input('SWITCH_hideAxes_3D', 'on'),
  prevent_initial_call = True
)
def switch_hideAxis(hideAxis):
  patch = Patch()
  if hideAxis:
    patch['layout']['scene']['xaxis']['visible'] = False
    patch['layout']['scene']['yaxis']['visible'] = False
    patch['layout']['scene']['zaxis']['visible'] = False
  else:
    patch['layout']['scene'] = dict(
        xaxis = {
                'visible': True,
                'backgroundcolor' :"white",
                'showbackground': True,
                'zerolinecolor': 'grey',
                'gridcolor': 'grey',
                'nticks': 6},
        yaxis = {
                'visible': True,
                'backgroundcolor' :"white",
                'showbackground': True,
                'zerolinecolor': 'grey',
                'gridcolor': 'grey',
                'nticks': 6},
        zaxis = {
                'visible': True,
                'backgroundcolor' :"white",
                'showbackground': True,
                'zerolinecolor': 'grey',
                'gridcolor': 'grey',
                'nticks': 6},
        bgcolor = 'white'
      )

  return patch, patch

# Store xyz ranges
@app.callback(
  Output('STORE_previewRange_3D', 'data'),
  Input('Slider_Xrange_3D', 'value'),
  Input('Slider_Yrange_3D', 'value'),
  Input('Slider_Zrange_3D', 'value'),
)
def store_xyzRange(x_range,y_range,z_range):
  return  {'x_min': x_range[0], 'x_max': x_range[1], 
           'y_min': y_range[0], 'y_max': y_range[1], 
           'z_min': z_range[0], 'z_max': z_range[1]}
  
@app.callback(
  Output('STORE_sliceRange_3D', 'data'),
  Input('cal_moranSVG', 'n_clicks'),
  State('STORE_previewRange_3D', 'data'),
  prevent_initial_call=True
)
def store_xyzCutRange(click, data):
  if click:
    return data

# Show selector box
@app.callback(
  
  Output('FIGURE_3Dexpression', 'figure', allow_duplicate=True),
  Output('FIGURE_3Dcelltype', 'figure', allow_duplicate=True),
  
  Input('SWITCH_previewBox_3D', 'on'),
  Input('STORE_previewRange_3D', 'data'),
  
  prevent_initial_call = True
)
def switch_showSelectorBox(showBox, range):
  patch = Patch()
  if showBox:
    patch['data'][-1] = go.Mesh3d(
        x=[range['x_min'], range['x_min'], range['x_min'], range['x_min'], range['x_max'], range['x_max'], range['x_max'], range['x_max']],
        y=[range['y_min'], range['y_max'], range['y_min'], range['y_max'], range['y_min'], range['y_max'], range['y_min'], range['y_max']],
        z=[range['z_min'], range['z_min'], range['z_max'], range['z_max'], range['z_min'], range['z_min'], range['z_max'], range['z_max']],
        i = [0, 1, 0, 0, 0, 0, 2, 2, 7, 7, 7, 7],
        j = [1, 2, 4, 1, 4, 2, 3, 6, 4, 4, 1, 1],
        k = [2, 3, 5, 5, 6, 6, 7, 7, 6, 5, 3, 5],
        color='black', opacity=0.60
      )
    return patch, patch
  else:
    if patch['data'][-1] == go.Mesh3d(x=[0,0], y=[0,0], z=[0,0]):
      raise PreventUpdate
    else:
      patch['data'][-1] = go.Mesh3d(x=[0,0], y=[0,0], z=[0,0])
    return patch, patch


# In[] callbacks/series :

@app.callback(
  Output('spatial_plotFeatureSeries_img', 'src', allow_duplicate=True),
  Output('spatial_plotFeatureSeries_ctpCounts_img', 'src', allow_duplicate=True),
  State('spatial_dropdown_featureType_series', 'value'),
  State('spatial_input_featureName_series', 'value'),
  Input('spatial_inputButton_featureName_series_plot', 'n_clicks'),
  State('spatial_dropdown_stage_series', 'value'),
  background=True,
  manager=background_callback_manager,
  running=[
    (Output('spatial_inputButton_featureLists_series_plot', 'children', allow_duplicate=True), 'Loading', 'Plot'),
    (Output('spatial_inputButton_featureLists_series_plot', 'disabled', allow_duplicate=True), True, False),
    (Output('spatial_inputButton_featureLists_series_plot', 'color', allow_duplicate=True), 'danger', 'primary'),
    (Output('spatial_textarea_featureLists_series', 'disabled', allow_duplicate=True),True, False),
    (Output('spatial_inputButton_featureName_series_plot', 'children', allow_duplicate=True), 'Loading', 'Plot'),
    (Output('spatial_inputButton_featureName_series_plot', 'disabled', allow_duplicate=True), True, False),
    (Output('spatial_inputButton_featureName_series_plot', 'color', allow_duplicate=True), 'danger', 'primary'),
    (Output('spatial_input_featureName_series', 'disabled', allow_duplicate=True),True, False),
  ],
  prevent_initial_call = True
)
def update_spatial_plotFeature_graphSeries_pattern(featureType, pattern, click, stage):
  if pattern is None:
    raise PreventUpdate

  if click:
    pattern = '^'+pattern
    if featureType == 'Gene':
      adata = exp_data[stage]
    elif featureType == 'Regulon':
      adata = auc_mtx[stage]

    # img_dir1 = show_features_spatial_regularExp(adata, stage, pattern, 'plotFeatureSeries', featureType, embedding = coord_data[stage][['x_flatten', 'y_flatten']], sort=True, ascending=True,)
    # img_dir2 = show_featuresCtpcounts_spatial_regularExp(adata, stage, pattern, 'plotFeatureSeries', featureType, embedding = coord_data[stage][['x_flatten', 'y_flatten']], sort=True, ascending=True,)
    with futures.ThreadPoolExecutor(max_workers=8) as executor:
      t1 = executor.submit(show_features_spatial_regularExp, adata, stage, 'plotFeatureSeries', featureType, 
                              pattern=pattern, embedding = coord_data[stage][['x_flatten', 'y_flatten']], sort=True, ascending=True)
      t2 = executor.submit(show_featuresCtpcounts_spatial_regularExp, adata, stage,'plotFeatureSeries', featureType, 
                              pattern=pattern, embedding = coord_data[stage][['x_flatten', 'y_flatten']], sort=True, ascending=True)
      img_dir1 = t1.result()
      img_dir2 = t2.result()
    return Image.open(img_dir1), Image.open(img_dir2)
  else:
    raise PreventUpdate


@app.callback(
  Output('spatial_plotFeatureSeries_img', 'src', allow_duplicate=True),
  Output('spatial_plotFeatureSeries_ctpCounts_img', 'src', allow_duplicate=True),
  State('spatial_dropdown_featureType_series', 'value'),
  State('spatial_textarea_featureLists_series', 'value'),
  Input('spatial_inputButton_featureLists_series_plot', 'n_clicks'),
  State('spatial_dropdown_stage_series', 'value'),
  background=True,
  manager=background_callback_manager,
  running=[
    (Output('spatial_inputButton_featureLists_series_plot', 'children', allow_duplicate=True), 'Loading', 'Plot'),
    (Output('spatial_inputButton_featureLists_series_plot', 'disabled', allow_duplicate=True), True, False),
    (Output('spatial_inputButton_featureLists_series_plot', 'color', allow_duplicate=True), 'danger', 'primary'),
    (Output('spatial_textarea_featureLists_series', 'disabled', allow_duplicate=True),True, False),
    (Output('spatial_inputButton_featureName_series_plot', 'children', allow_duplicate=True), 'Loading', 'Plot'),
    (Output('spatial_inputButton_featureName_series_plot', 'disabled', allow_duplicate=True), True, False),
    (Output('spatial_inputButton_featureName_series_plot', 'color', allow_duplicate=True), 'danger', 'primary'),
    (Output('spatial_input_featureName_series', 'disabled', allow_duplicate=True),True, False),
  ],
  prevent_initial_call = True
)
def update_spatial_plotFeature_graphSeries_list(featureType, names, click, stage):
  if names is None:
    raise PreventUpdate

  if click:

    names = re.split(", |,| |\n|\'|\"|#|-|_|%|$|@|\(|\)|\||^|&", names)
    names = [i for i in names if i]

    if featureType == 'Gene':
      adata = exp_data[stage]
    elif featureType == 'Regulon':
      adata = auc_mtx[stage]

    with futures.ThreadPoolExecutor(max_workers=8) as executor:
      t1 = executor.submit(show_features_spatial_regularExp, adata, stage,  'plotFeatureSeries', featureType,
                            features=names, embedding = coord_data[stage][['x_flatten', 'y_flatten']], sort=True, ascending=True)
      t2 = executor.submit(show_featuresCtpcounts_spatial_regularExp, adata, stage,'plotFeatureSeries', featureType,
                            features=names, embedding = coord_data[stage][['x_flatten', 'y_flatten']], sort=True, ascending=True)
      img_dir1 = t1.result()
      img_dir2 = t2.result()
    return Image.open(img_dir1), Image.open(img_dir2)
  else:
    raise PreventUpdate

@app.callback(
  Output('spatial_plotFeatureSeries_graph_ctp', 'figure'),
  Input('spatial_dropdown_stage_series', 'value'),
)
def update_spatial_plotFeatureSeries_ctpGraph(stage):
  fig = show_celltype_spatial(exp_data[stage], embedding = coord_data[stage][['x_flatten', 'y_flatten']],
                             facet_col = 'germ_layer', category_orders={'germ_layer':['ectoderm','mesoderm','endoderm']})
  fig.update_layout(
    legend = {
      'orientation': 'h'
    }
  )
  return fig


# In[] callbacks/sparkx:

@app.callback(
  [
    Output('spatial_dataTable_sparkx', 'data'),
    Output('spatial_dataTable_sparkx', 'columns'),
    # Output('clientside_store_table_sparkx', 'data'),
  ],
  [
    Input('spatial_dropdown_stage_sparkx', 'value'),
    State('spatial_dropdown_featureType_sparkx', 'value'),
  ]
)
def choose_sparkx_plotOptions(stage, featureType):
  if not stage:
    raise PreventUpdate
  df = genes_all_pval.loc[stage].reset_index().rename(columns={"index": "gene"})
  df['id'] = df['gene']
  return (df.to_dict('records'), 
          [{"name": i, "id": i, "deletable": False, 'type': 'numeric', 
              'format':Format(precision=2, scheme=Scheme.exponent)} 
             if i != 'gene' else
             {"name": i, "id": i, "deletable": False} 
             for i in df.columns if i != 'id'],
          # {'data': df.to_dict('records'),
          # 'columns': [{"name": i, "id": i, "deletable": False, 'type': 'numeric', 
          #               'format':Format(precision=2, scheme=Scheme.exponent)} 
          #            if i != 'gene' else
          #              {"name": i, "id": i, "deletable": False} 
          #            for i in df.columns if i != 'id']},
          )

@app.callback(
  Output('spatial_dataTable_sparkx', 'page_size'),
  Input('spatial_dropdown_pageSize_sparkx', 'value'),
)
def update_sprkx_tablePageSize(pageSize):
  if not pageSize:
    raise PreventUpdate
  else:
    return pageSize
  
@app.callback(
  [
    Output('spatial_dataTable_sparkx', 'style_data_conditional'),
  ],
  [
    Input('spatial_dataTable_sparkx', 'derived_viewport_selected_row_ids'),
  ],
  prevent_initial_call=True
)
def update_highlightRow_store(rows):
  if not rows:
    raise PreventUpdate
  row_highlighting = [
      {
          'if': {"filter_query": "{{id}} ={}".format(i)},
          'background_color': 'tomato',
          'color': 'white'
      } for i in rows
  ]
  return (row_highlighting,)

@app.callback(
  [
    Output('spatial_featureGraph_sparkx', 'figure'),
  ],
  [
    Input('spatial_dataTable_sparkx', 'selected_row_ids'),
    Input('spatial_dropdown_stage_sparkx', 'value'),
    Input('spatial_dropdown_featureType_sparkx', 'value')
  ],
  prevent_initial_call=True,
  background=True,
  manager=background_callback_manager,
)
def choose_sparkx_featureToPlot(row_id, stage, featureType):
  if not row_id:
    raise PreventUpdate
  if featureType == 'Gene':
    adata = exp_data[stage]
  elif featureType == 'Regulon':
    adata = auc_mtx[stage]

  return (
    show_feature_spatial(adata, row_id[0], embedding = coord_data[stage][['x_flatten', 'y_flatten']], sort=True, ascending=True,
                            facet_col = 'germ_layer', category_orders={'germ_layer':['ectoderm','mesoderm','endoderm']}),
  )

@app.callback(
  [
    Output('spatial_celltypeGraph_sparkx', 'figure'),
  ],
  [
    Input('spatial_dropdown_stage_sparkx', 'value'),
  ],
  background=True,
  manager=background_callback_manager,
)
def update_sparkx_stageCtpGraph(stage):
  if not stage:
    raise PreventUpdate
  return (
      show_celltype_spatial(exp_data[stage], embedding = coord_data[stage][['x_flatten', 'y_flatten']],
                           facet_col = 'germ_layer', category_orders={'germ_layer':['ectoderm','mesoderm','endoderm']}),
  )

# In[] app/run:

tabs = dbc.Col(
  spatial_tabs,
  id = 'tabs'
)

app.layout = dbc.Container(
  [
    header,
    dbc.Row([
      # dbc.Col([
      #   controls,
      # ], width=2),
      dbc.Col([
        tabs,
      ], width=12)
    ],)
  ],
  fluid=True,
  className="SET-all",
)


if __name__ == "__main__":
    app.run(
    host='10.193.0.208',
    port='8051',
    # threaded=True,
    proxy=None,
    debug=True,
    use_reloader=False,
    jupyter_mode='external',
)




# %% test

# %%