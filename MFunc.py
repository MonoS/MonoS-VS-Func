import vapoursynth as vs
import havsfunc as has
import nnedi3_resample as res
import os.path

def WriteVecs(vecs, prefix):
	core = vs.get_core()
	
	w = vecs[0].get_frame(0).width
	
	v = core.std.StackVertical([core.std.CropAbs(vec, width=w, height=1) for vec in vecs])
	
	log = open(prefix + ".len", "w")
	log.write(repr(w))
	log.close()
	
	return v

def ReadVecs(index, prefix, h):
	core = vs.get_core()
	
	f = open(prefix + ".len", "r")
	w = int(f.read())
	f.close()
	
	vecs = core.raws.Source(prefix + ".vec", w, h, src_fmt="Y8")
	
	v = core.std.CropAbs(vecs, y=index, height=1, width=w)
	
	return v
	
def Denoise2(src, denoise=400, blur=None, lsb=True, truemotion=True, chroma=True, fast=False, blksize=None):
	core = vs.get_core()
	
	src16 = Up16(src, lsb)
	
	if fast:
		if blksize is None:
			blksize = 32
		
		overlap = int(blksize/4)
	else:
		if blksize is None:
			blksize = 8
		
		overlap = int(blksize/2)
	
	if blur is not None:
		blurred = core.generic.GBlur(src, blur, planes = [0,1,2] if chroma else [0])
		blurred = Up16(blurred, lsb) if lsb else blurred
	else:
		blurred = src16
	
	rep = has.DitherLumaRebuild(blurred, s0=1, chroma=chroma)
	superRep = core.mv.Super(rep, chroma=chroma)
	
	super = core.mv.Super(src16, chroma=chroma)
	
	if prefix is not None:
		exist = os.path.exists(prefix + ".vec") and os.path.exists(prefix + ".len")
		create = not exist
	else:
		exist = False
		create = False
	
	if not exist:
		bvec2 = core.mv.Analyse(superRep, isb = True, delta = 2, blksize=blksize, overlap=overlap, truemotion=truemotion, chroma=chroma)
		bvec1 = core.mv.Analyse(superRep, isb = True, delta = 1, blksize=blksize, overlap=overlap, truemotion=truemotion, chroma=chroma)
		fvec1 = core.mv.Analyse(superRep, isb = False, delta = 1, blksize=blksize, overlap=overlap, truemotion=truemotion, chroma=chroma)
		fvec2 = core.mv.Analyse(superRep, isb = False, delta = 2, blksize=blksize, overlap=overlap, truemotion=truemotion, chroma=chroma)
		if create:
			return WriteVecs([bvec1, bvec2, fvec1, fvec2], prefix)
	else:
		bvec1 = ReadVecs(0, prefix, 4)
		bvec2 = ReadVecs(1, prefix, 4)
		fvec1 = ReadVecs(2, prefix, 4)
		fvec2 = ReadVecs(3, prefix, 4)
		
	fin = core.mv.Degrain2(src16, super, bvec1,fvec1,bvec2,fvec2, denoise, plane = 4 if chroma else 0)
	
	return fin

def GCResizer(src, w, h, Ykernel=None, UVkernel=None, Yinvks=False, UVinvks=None, Yinvkstaps=3, UVinvkstaps=None, Ytaps=4, UVtaps=None, css="420", sigmoid=True, curve="709", mat="709", scaleThr=1.0):
	core = vs.get_core()
	
	src16 = Up16(src)
	
	csp = vs.YUV444P16 if css == "444" else None
	
	if Ykernel is None:
		if Yinvks:
			Ykernel = "bilinear"
		else:
			Ykernel = "spline64"
	
	UVinvks = UVinvks if UVinvks is not None else Yinvks
	
	if UVkernel is None:
		if UVinvks:
			UVkernel = "bicubic"
		else:
			UVkernel = Ykernel
	
	UVinvkstaps = UVinvkstaps if UVinvkstaps is not None else Yinvkstaps
	
	UVtaps = UVtaps if UVtaps is not None else Ytaps
	
	resized = res.nnedi3_resample(src16, w, h, kernel=Ykernel, chromak_down=UVkernel, invks=Yinvks, chromak_down_invks=UVinvks, invkstaps=Yinvkstaps, chromak_down_invkstaps=UVinvkstaps, taps=Ytaps, chromak_down_taps=UVtaps, mats=mat, fulls=False, curves=curve, sigmoid=sigmoid, scale_thr=scaleThr, csp=csp)
	
	return resized

def MQTGMC(src, EZDenoise=None, lsb=None, TFF=True, half=False, fast=False):
	core = vs.get_core()
	
	if lsb is None:
		if fast is True:
			lsb = False
		else:
			lsb = True
	
	src16 = Up16(src, lsb)
	
	FPSDivisor = 2 if half else 1
	
	# Controllare MatchEnhance e/o Sharpness in quanto con SourceMatch il risultato sembra essere meno sharposo
	
	# has.QTGMC(src16, Preset="Very Slow", SourceMatch=3, MatchPreset="Slow", MatchPreset2="Ultra Fast",  Lossless=2, NoisePreset="Slow", TFF=TFF, EZDenoise=EZDenoise, FPSDivisor=FPSDivisor)
	# has.QTGMC(src16, Preset="Medium", SourceMatch=3, MatchPreset="Fast", MatchPreset2="Ultra Fast",  Lossless=2, NoisePreset="Medium", TFF=TFF, EZDenoise=EZDenoise, FPSDivisor=FPSDivisor)
	
	if fast:
		result = has.QTGMC(src16, Preset="Medium", SourceMatch=3, MatchPreset="Fast", Lossless=2, NoisePreset="Medium", TFF=TFF, EZDenoise=EZDenoise, FPSDivisor=FPSDivisor)
	else:
		result = has.QTGMC(src16, Preset="Very Slow", SourceMatch=3, MatchPreset2="Slow", Lossless=2, NoisePreset="Slow", TFF=TFF, EZDenoise=EZDenoise, FPSDivisor=FPSDivisor)
	
	return result

def Up16(src, lsb=True):
	core = vs.get_core()
	
	src16 = src
	if(lsb is True) and (src.format.bits_per_sample < 16):
		src16 = core.fmtc.bitdepth(src, bits=16)
	
	return src16