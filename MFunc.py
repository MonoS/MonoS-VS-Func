import vapoursynth as vs
import Dither as dit
import havsfunc as has

def Denoise2(src, denoise=400, blur=None, lsb=True, truemotion=True, chroma=True):
	core = vs.get_core()
	
	src16 = src
	if(lsb is True):
		if(src.format.bits_per_sample == 8):
			src16 = core.fmtc.bitdepth(src, bits=16)
		else:
			src16 = src
	else:
		src16 = src
	
	if blur is not None:
		blurred = core.generic.GBlur(src16, blur)
	else:
		blurred = src16
	
	super = core.mv.Super(blurred, chroma=chroma)
	backward_vec2 = core.mv.Analyse(super, isb = True, delta = 2, overlap=4, truemotion=truemotion, chroma=chroma)
	backward_vec1 = core.mv.Analyse(super, isb = True, delta = 1, overlap=4, truemotion=truemotion, chroma=chroma)
	forward_vec1 = core.mv.Analyse(super, isb = False, delta = 1, overlap=4, truemotion=truemotion, chroma=chroma)
	forward_vec2 = core.mv.Analyse(super, isb = False, delta = 2, overlap=4, truemotion=truemotion, chroma=chroma)
	fin = core.mv.Degrain2(src16, super, backward_vec1,forward_vec1,backward_vec2,forward_vec2, denoise, plane = 4 if chroma else 0)
	
	return fin

def GCResizer(src, w, h, curve, Ykernel="spline64", UVkernel=None, Yinvks=False, UVinvks=None, sigmoid=True, Yrfactor=2, UVrfactor=None, Yinvkstaps=3, UVinvkstaps=None, Ytaps=4, UVtaps=None, css="420"):
	core = vs.get_core()
	
	if UVkernel is None:
		UVkernel = Ykernel
	
	if UVinvks is None:
		UVinvks = Yinvks
	
	if UVinvkstaps is None:
		UVinvkstaps = Yinvkstaps
	
	if UVtaps is None:
		UVtaps = Ytaps
	
	if UVrfactor is None:
		UVrfactor = Yrfactor
	
	wrt = w / src.width
	hrt = h / src.height
	
	src16 = src
	if(src.format.bits_per_sample < 16):
		src16 = core.fmtc.bitdepth(src, bits=16)
	
	YUpscale = False
	UVUpscale = False
	if((wrt > 1.0) or (hrt > 1.0)):
		Yupscale = True
		UVUpscale = True
	
	if((src16.format.id == vs.YUV420P16) and (css != "420") and ((wrt > 0.5) or (hrt > 0.5))):
		UVUpscale = True
	
	YTouch = True
	if((wrt == 1.0) and (hrt == 1.0)):
		YTouch = False
	
	Y = core.std.ShufflePlanes(src16, [0], vs.GRAY)
	UV = src16
	
	if YTouch:
		YLin = dit.gamma_to_linear(Y, fulls=False, curve=curve, sigmoid=sigmoid)
	else:
		YLin = Y
	
	if YUpscale:
		YLinUp = core.nnedi3.nnedi3_rpow2(YLin, Yrfactor)
	else:
		YLinUp = YLin
	
	if UVUpscale:
		UVUp = core.nnedi3.nnedi3_rpow2(UV, UVrfactor, correct_shift=True)
	else:
		UVUp = UV
	
	if YTouch:
		YLinDown = core.fmtc.resample(YLinUp, w, h, kernel=Ykernel, invks=Yinvks, invkstaps=Yinvkstaps, taps=Ytaps)
	else:
		YLinDown = YLinUp
	
	if((wrt != 0.5) and (hrt != 0.5)):
		UVDown = core.fmtc.resample(UVUp, w, h, kernel=UVkernel, invks=UVinvks, invkstaps=UVinvkstaps, taps=UVtaps, planes=[1,3,3], css=css)
	else:
		UVDown = UVUp
	
	if YTouch:
		YGammaDown = dit.linear_to_gamma(YLinDown, fulls=False, curve=curve, sigmoid=sigmoid)
	else:
		YGammaDown = YLinDown
	
	YUV = core.std.ShufflePlanes([YGammaDown, UVDown], [0,1,2], vs.YUV)
	
	return YUV

def MQTGMC(src, EZDenoise=None, lsb=True, TFF=True, half=False):
	core = vs.get_core()
	
	src16 = src
	if(lsb is True):
		if(src.format.bits_per_sample == 8):
			src16 = core.fmtc.bitdepth(src, bits=16)
		else:
			src16 = src
	else:
		src16 = src
	
	FPSDivisor = 2 if half else 1
	
	result = has.QTGMC(src16, Preset="Very Slow", SourceMatch=3, MatchPreset2="Slow", Lossless=2, NoisePreset="Slow", TFF=TFF, EZDenoise=EZDenoise, FPSDivisor=FPSDivisor)
	
	return result