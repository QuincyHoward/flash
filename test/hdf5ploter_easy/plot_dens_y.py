import h5py, matplotlib.pyplot as plt, numpy as np

# PPT-friendly plot style (fonts >= 18, English only)
try:
    from output_processors.plotter.plot_style import apply_plot_style
    apply_plot_style()
except ImportError:
    pass
f=h5py.File('lasslab_hdf5_plt_cnt_0066','r')
b=f['bounding box'][:]; d=f['dens'][:,0,0,:]
t=np.linspace(0,1,d.shape[1])
x=(b[:,0,:1]*(1-t)+b[:,0,1:]*t).ravel()
plt.plot(x[np.argsort(x)],d.ravel()[np.argsort(x)])
plt.xlabel('x (cm)'); plt.ylabel(r'density (g/cm$^3$)')
plt.savefig('dens_plot.png',dpi=200)
