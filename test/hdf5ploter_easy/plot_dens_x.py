import h5py, matplotlib.pyplot as plt, numpy as np

# PPT-friendly plot style (fonts >= 18, English only)
try:
    from output_processors.plotter.plot_style import apply_plot_style
    apply_plot_style()
except ImportError:
    pass
f=h5py.File('lasslab_hdf5_plt_cnt_0066','r')
b=f['bounding box'][:]; d=f['dens'][:,0,0,:]
x=np.concatenate([np.linspace(b[i,0,0],b[i,0,1],d.shape[1]) for i in range(len(b))])
den=np.concatenate([d[i] for i in range(len(d))])
i=np.argsort(x)
plt.plot(x[i],den[i]);
plt.xlabel('x (cm)'); plt.ylabel(r'density (g/cm$^3$)')
plt.savefig('dens_plot.png',dpi=200)