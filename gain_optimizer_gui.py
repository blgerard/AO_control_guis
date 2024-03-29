'''
write simple code to optimize the gain AO gain by minimizing the quadratic sum of atmospheric and noise components of an AO system.
'''

from matplotlib.widgets import Slider, Button, RadioButtons
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import scipy


#magnitude and phase of transfer functions:
mag = lambda tf: 20.*np.log10(np.sqrt(np.real(tf)**2.+np.imag(tf)**2.)) #magnitude in dB
phase = lambda tf: np.unwrap(np.arctan2(np.imag(tf),np.real(tf)))*180./np.pi #np.unwrap prevents 2 pi phase discontinuities
s2f = lambda f: 1.j*2.*np.pi*f

#transfer functions
Hwfs = lambda s, Ts: (1. - np.exp(-Ts*s))/(Ts*s)
Hzoh=Hwfs
Hlag = lambda s,tau: np.exp(-tau*s)
leak=0.99
Hcont = lambda s, Ts, g: g/(1. - leak*np.exp(-Ts*s)) #leaky integrator
Holsplane = lambda s, Ts, tau, g:  Hwfs(s, Ts)*Hlag(s,tau)*Hcont(s,Ts,g)*Hzoh(s,Ts)
Hol = lambda f, Ts, tau, g:  Holsplane(1.j*2.*np.pi*f,Ts,tau,g)
Hrej = lambda f, Ts, tau, g: 1./(1. + Hol(f, Ts, tau, g))
Hn = lambda f, Ts, tau, g: Hol(f, Ts, tau, g)*Hrej(f, Ts, tau, g)/Hwfs(1.j*2.*np.pi*f, Ts)

fontsize=14
font = {'family':'Times New Roman', 'size':fontsize}
mpl.rc('font',**font)

v,D=20.,8. #wind speed and telescope diameter in meters/s and meters, respectively
#initial values
ttrms=0.3 #0.3" tip tilt rms
pl=-2. #chosen power law to use for T/T PSD
T_s,tau=1e-3,1e-3
seeing=1.5 #seeing in arcsec
m_object=15. #R band magnitude of guide star

gain_ini=np.linspace(0.01,1.,500)

def opt(seeing,ttrms,m_object,v,D,pl,T_s,tau):
	freq = lambda T_s: np.logspace(np.log10(0.1),np.log10(1./(2.*T_s)),500) #only plot up to the Nyquist limit 
	f=freq(T_s)

	#calculate number of photons coming to the telescope given a R band magnitude
	f0=1.35e10 #photons/m**2/s, rband, mag 0 star
	flux_object_ini=f0*10.**(-m_object/2.5)
	tr_atm,qe=0.7,0.8 #assume transmission through the atmosphere, quantum efficiency of CCD
	flux_object=flux_object_ini*tr_atm*qe
	Nphot=flux_object*T_s*np.pi*(D/2.)**2. 


	#define noise PSD
	flat_PSD_unscaled=f/f
	norm_flat_psd=np.trapz(flat_PSD_unscaled,f)
	NEA=seeing/2./np.sqrt(Nphot)
	PSDn=flat_PSD_unscaled/norm_flat_psd*NEA**2.


	#define tip-tilt PSD:
	knee=np.where(f>0.3*v/D)
	coeff=1./f[min(knee[0])]**pl
	PSDtt_unscaled=f/f
	PSDtt_unscaled[knee]=coeff*f[knee]**(pl)
	norm=np.trapz(PSDtt_unscaled,f)
	PSDtt=PSDtt_unscaled/norm*ttrms**2.

	square_modulus = lambda tf: np.real(tf)**2.+np.imag(tf)**2.

	#loop through different gain values to calculate 
	wfe=np.array([])
	gain=np.array([])
	for g in gain_ini:
		phol=phase(Hol(f,T_s,tau,g))
		magol=mag(Hol(f,T_s,tau,g))
		ind_margin=np.where(np.abs(magol)==np.min(np.abs(magol))) #this is where the modulus of the tranfer function is 1

		if phol[ind_margin]+180. > 45.:
			#residual noise variance
			var_n=np.trapz(PSDn*square_modulus(Hn(f,T_s,tau,g)),f)
			#residual tt variance
			var_tt=np.trapz(PSDtt*square_modulus(Hrej(f,T_s,tau,g)),f)
			#minimize atmospheric plus noise variance
			wfe=np.append(wfe,np.sqrt(var_tt+var_n))
			gain=np.append(gain,g)

	return gain,wfe

gain,wfe=opt(seeing,ttrms,m_object,v,D,pl,T_s,tau)

fig=plt.figure()
ax=plt.subplot(111)
ax.set_xlabel('gain')
ax.set_ylabel('$\sqrt{\sigma_{atm}^2+\sigma_{n}^2}$ (arcseconds rms)')
[line]=ax.plot(gain,wfe,color='blue',lw=2,alpha=0.5)
indgain=np.where(np.abs(wfe)==np.min(np.abs(wfe)))[0][0]
mwfe=wfe[indgain]
minwfe=ax.axhline(mwfe,color='purple',lw=2,linestyle='--',alpha=0.5)
mgain=gain[indgain]
mingain=ax.axvline(mgain,color='red',lw=2,linestyle='--',alpha=0.5)
ax.set_title('WFE='+str(round(mwfe,3))+' arcsec rms, g$_{opt}=$'+str(round(mgain,3)))
ax.grid('on')
ax.set_ylim(0.,1.)
ax.set_xlim(0.,1.)


fig.subplots_adjust(bottom=0.55,top=0.9,left=0.15)

ttrms_ax  = fig.add_axes([0.30, 0.4, 0.55, 0.03])
v_ax  = fig.add_axes([0.30, 0.35, 0.55, 0.03])
d_ax  = fig.add_axes([0.30, 0.3, 0.55, 0.03])
pl_ax  = fig.add_axes([0.30, 0.25, 0.55, 0.03])
m_object_ax  = fig.add_axes([0.30, 0.2, 0.55, 0.03])
seeing_ax  = fig.add_axes([0.30, 0.15, 0.55, 0.03])
ts_ax  = fig.add_axes([0.30, 0.07, 0.55, 0.03])
tau_ax  = fig.add_axes([0.30, 0.03, 0.55, 0.03])

ttrms_slider = Slider(ttrms_ax, 'tip/tilt rms (arcsec)',0.1,1.5, valinit=ttrms)
v_slider = Slider(v_ax, 'wind speed (m/s)',2,30, valinit=v)
d_slider = Slider(d_ax, 'telescope diameter (m)',1.,10., valinit=D)
pl_slider = Slider(pl_ax, 'tip/tilt PSD power law',-5,-0.5, valinit=pl)
m_object_slider = Slider(m_object_ax, 'target R mag',5.,20., valinit=m_object)
seeing_slider = Slider(seeing_ax, 'seeing (arcsec)',0.3,2.0, valinit=seeing)
ts_slider = Slider(ts_ax, 'T$_s$ (s)',0.1e-3,3e-3, valinit=T_s,valfmt='%.2e')
tau_slider = Slider(tau_ax, '$\\tau$ (s)',0.1e-3,3e-3, valinit=tau,valfmt='%.2e')

def sliders_on_changed(val):
	seeing=seeing_slider.val
	ttrms=ttrms_slider.val
	m_object=m_object_slider.val
	v=v_slider.val
	D=d_slider.val
	pl=pl_slider.val
	T_s=ts_slider.val
	tau=tau_slider.val

	gain,wfe=opt(seeing,ttrms,m_object,v,D,pl,T_s,tau)

	indgain=np.where(np.abs(wfe)==np.min(np.abs(wfe)))
	mwfe=wfe[indgain]
	mgain=gain[indgain]

	line.set_data(gain,wfe)
	minwfe.set_ydata(mwfe)
	mingain.set_xdata(mgain)
	ax.set_title('WFE='+str(round(mwfe,3))+' arcsec rms, g$_{opt}=$'+str(round(mgain,3)))


	fig.canvas.draw_idle()

seeing_slider.on_changed(sliders_on_changed)
ttrms_slider.on_changed(sliders_on_changed)
m_object_slider.on_changed(sliders_on_changed)
v_slider.on_changed(sliders_on_changed)
d_slider.on_changed(sliders_on_changed)
pl_slider.on_changed(sliders_on_changed)
ts_slider.on_changed(sliders_on_changed)
tau_slider.on_changed(sliders_on_changed)