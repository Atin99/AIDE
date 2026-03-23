
from dataclasses import dataclass, field
from typing import Optional

@dataclass(frozen=True)
class Element:
    Z:               int
    symbol:          str
    name:            str
    atomic_mass:     float
    period:          int
    group:           Optional[int]
    block:           str

    Tm:              Optional[float]
    Tb:              Optional[float]
    density:         Optional[float]
    thermal_exp:     Optional[float]
    thermal_cond:    Optional[float]
    debye_T:         Optional[float]

    E:               Optional[float]
    G:               Optional[float]
    B:               Optional[float]
    nu:              Optional[float]
    vickers:         Optional[float]

    electronegativity: Optional[float]
    valence_e:       int
    oxidation_states: tuple
    resistivity:     Optional[float]
    work_function:   Optional[float]

    radius:          Optional[float]
    crystal:         Optional[str]

    mag_type:        str
    mag_moment:      Optional[float]
    curie_T:         Optional[float]

    neutron_xs:      Optional[float]
    radioactive:     bool

    surface_energy:  Optional[float]
    d_band_centre:   Optional[float]

    lambda_ep:       Optional[float]
    Tc_sc:           Optional[float]

    rohs_restricted: bool
    reach_svhc:      bool
    carcinogen_iarc: Optional[str]


_DB: dict = {}

def _e(Z,sym,name,mass,per,grp,blk,
       Tm,Tb,den,alpha,kappa,debye,
       E,G,B,nu,hv,
       chi,val,ox,rho,wf,
       r,xtal,
       mag,mu,Tc,
       xs,radio,
       gam_s,d_band,
       lam,Tc_sc,
       rohs,svhc,iarc):
    el = Element(Z,sym,name,mass,per,grp,blk,
                 Tm,Tb,den,alpha,kappa,debye,
                 E,G,B,nu,hv,
                 chi,val,ox,rho,wf,
                 r,xtal,
                 mag,mu,Tc,
                 xs,radio,
                 gam_s,d_band,
                 lam,Tc_sc,
                 rohs,svhc,iarc)
    _DB[sym]=el; _DB[str(Z)]=el

# fmt: Z sym name mass per grp blk | Tm Tb den α κ θD | E G B ν HV | χ val ox ρ WF | r xtal | mag μ Tc | xs radio | γ_s d_band | λ Tc_sc | rohs svhc iarc
_e( 1,'H' ,'Hydrogen'   , 1.008,1, 1,'s', 14.0,  20.3, 0.0709,None, 0.18, 110,
    None,None,None,None,None, 2.20,1,(-1,1),None,None, 53,None,'dia',None,None,
    0.33,False, None,None, None,None, False,False,None)
_e( 2,'He','Helium'     , 4.003,1,18,'s',  0.95,  4.22,0.1640,None,0.150,  26,
    None,None,None,None,None, None,0,()    ,None,None, 31,None,'dia',None,None,
    0.0, False, None,None, None,None, False,False,None)

_e( 3,'Li','Lithium'    , 6.941,2, 1,'s',453.7,1615.0, 0.534,46.0, 84.8, 344,
     4.9, 4.2, 11.0,0.360,  40, 0.98,1,(1,),  9.47,2.93,167,'BCC','para',None,None,
    71.0,False, 0.51,None, None,None, False,False,None)
_e( 4,'Be','Beryllium'  , 9.012,2, 2,'s',1560.0,2742.,1.848,11.3,200.0,1440,
    287.,132.,130.0,0.032,1670, 1.57,2,(2,),  4.0 ,4.98,112,'HCP','dia',None,None,
    0.009,False, 1.40,None, None,None, True,True,'1')

_e( 5,'B' ,'Boron'      ,10.811,2,13,'p',2349.0,4200.0, 2.340, 6.0, 27.4,1480,
    None,None,None,None,None, 2.04,3,(-3,3),1e6,None, 87,'rhomb','dia',None,None,
    767.,False, None,None, None,None, False,False,None)
_e( 6,'C' ,'Carbon'     ,12.011,2,14,'p',3823.0,5100.0, 2.267, 0.71,119.,2230,
    1050.,None,None,0.10,None, 2.55,4,(-4,4),1375.,5.0, 77,'hex','dia',None,None,
    0.0035,False, 0.08,None, None,None, False,False,None)
_e( 7,'N' ,'Nitrogen'   ,14.007,2,15,'p',  63.1,  77.4,0.00125,None,0.026, 68,
    None,None,None,None,None, 3.04,5,(-3,3,5),None,None, 75,None,'dia',None,None,
    1.83,False, None,None, None,None, False,False,None)
_e( 8,'O' ,'Oxygen'     ,15.999,2,16,'p',  54.4,  90.2,0.00143,None,0.027, 90,
    None,None,None,None,None, 3.44,6,(-2,2), None,None, 73,None,'para',None,None,
    0.00019,False,None,None, None,None, False,False,None)
_e( 9,'F' ,'Fluorine'   ,18.998,2,17,'p',  53.5,  85.1,0.00170,None,0.027,None,
    None,None,None,None,None, 3.98,7,(-1,),  None,None, 64,None,'dia',None,None,
    0.0096,False,None,None, None,None, False,False,None)
_e(10,'Ne','Neon'        ,20.180,2,18,'p',  24.6,  27.1,0.00090,None,0.049, 63,
    None,None,None,None,None, None,0,(),     None,None, 38,None,'dia',None,None,
    0.04,False, None,None, None,None, False,False,None)

_e(11,'Na','Sodium'      ,22.990,3, 1,'s',370.9,1156.0, 0.968,71.0,141.0, 158,
    68., 29., 68.,0.330,None, 0.93,1,(1,),  4.77,2.35,190,'BCC','para',None,None,
    0.53,False, 0.26,None, None,None, False,False,None)
_e(12,'Mg','Magnesium'   ,24.305,3, 2,'s',923.0,1363.0, 1.738,24.8,156.0, 400,
    44.7,17.3, 36.8,0.290, 374, 1.31,2,(2,),  4.45,3.66,160,'HCP','para',None,None,
    0.063,False, 0.76,None, None,None, False,False,None)
_e(13,'Al','Aluminium'   ,26.982,3,13,'p',933.5,2792.0, 2.698,23.1,237.0, 428,
    70.0,26.1, 76.0,0.345, 160, 1.61,3,(3,),  2.82,4.28,143,'FCC','para',None,None,
    0.231,False, 1.16,None, 0.43,1.19, False,False,None)
_e(14,'Si','Silicon'     ,28.086,3,14,'p',1687.0,3538.0, 2.329, 2.6,149.0, 645,
    130., 79., 97.8,0.064,None, 1.90,4,(-4,4),1e5, 4.01,117,'diamond','dia',None,None,
    0.171,False, 1.24,None, None,None, False,False,None)
_e(15,'P' ,'Phosphorus'  ,30.974,3,15,'p',317.3, 554.0, 1.823,None, 0.236,None,
    None,None,None,None,None, 2.19,5,(-3,3,5),1e17,None,110,None,'dia',None,None,
    0.172,False, None,None, None,None, False,False,None)
_e(16,'S' ,'Sulphur'     ,32.060,3,16,'p',388.4, 717.8, 2.067,None, 0.269,None,
    None,None,None,None,None, 2.58,6,(-2,4,6),2e23,None,104,'ortho','dia',None,None,
    0.53,False, None,None, None,None, False,False,None)
_e(17,'Cl','Chlorine'    ,35.450,3,17,'p',171.6, 239.1,0.00321,None,0.0089,None,
    None,None,None,None,None, 3.16,7,(-1,1,3,5,7),None,None,99,None,'dia',None,None,
    33.5,False, None,None, None,None, False,False,None)
_e(18,'Ar','Argon'       ,39.948,3,18,'p', 83.8,  87.3,0.00178,None,0.0178, 85,
    None,None,None,None,None, None,0,(),    None,None, 71,None,'dia',None,None,
    0.675,False, None,None, None,None, False,False,None)

_e(19,'K' ,'Potassium'   ,39.098,4, 1,'s',336.5,1032.0, 0.856,83.3,102.0,  91,
    3.53,1.34, 3.1,0.360,None, 0.82,1,(1,),  7.20,2.29,243,'BCC','para',None,None,
    2.1,False,  0.13,None, None,None, False,False,None)
_e(20,'Ca','Calcium'     ,40.078,4, 2,'s',1115.0,1757.0, 1.550,22.3,200.0, 230,
    20.2, 7.9, 17.2,0.310, 170, 1.00,2,(2,),  3.91,2.87,197,'FCC','para',None,None,
    0.43,False, 0.49,None, None,None, False,False,None)
_e(21,'Sc','Scandium'    ,44.956,4, 3,'d',1814.0,3109.0, 2.985,10.2, 15.8, 360,
    74.4,29.1, 56.6,0.279,None, 1.36,3,(3,), 55.4, 3.5,162,'HCP','para',None,None,
    27.2,False, 1.27,None, None,None, False,False,None)
_e(22,'Ti','Titanium'    ,47.867,4, 4,'d',1941.0,3560.0, 4.507, 8.6, 21.9, 420,
    116., 44., 110.0,0.321, 990, 1.54,4,(2,3,4), 42.0, 4.33,147,'HCP','para',None,None,
    6.09,False, 2.04,-2.10, None,None, False,False,None)
_e(23,'V' ,'Vanadium'    ,50.942,4, 5,'d',2183.0,3680.0, 6.110, 8.4, 30.7, 380,
    128., 46.7,158.0,0.365, 628, 1.63,5,(2,3,4,5),25.0,4.44,134,'BCC','para',None,None,
    5.08,False, 2.62,-1.90, 1.00,5.40, False,False,None)
_e(24,'Cr','Chromium'    ,51.996,4, 6,'d',2180.0,2944.0, 7.190, 4.9, 93.9, 630,
    279.,115., 160.0,0.210,1060, 1.66,6,(2,3,6), 12.7, 4.50,128,'BCC','anti',3.0,311,
    3.07,False, 2.30,-1.70, 0.24,None, False,True,'3')
_e(25,'Mn','Manganese'   ,54.938,4, 7,'d',1519.0,2334.0, 7.210,21.7,  7.81, 400,
    198.,None, 120.0,None,None, 1.55,7,(2,3,4,7),185.,4.10,127,'cubic','anti',None,None,
    13.3,False, 1.54,-2.20, None,None, False,False,None)
_e(26,'Fe','Iron'        ,55.845,4, 8,'d',1811.0,3134.0, 7.874,11.8, 80.4, 470,
    211., 82., 170.0,0.293, 608, 1.83,8,(2,3),  9.71,4.67,126,'BCC','ferro',2.22,1043,
    2.56,False, 2.41,-1.50, None,None, False,False,None)
_e(27,'Co','Cobalt'      ,58.933,4, 9,'d',1768.0,3200.0, 8.900,13.0,100.0, 445,
    211., 75.5,180.0,0.310,1043, 1.88,9,(2,3),  6.24,5.00,125,'HCP','ferro',1.72,1388,
    37.2,False, 2.52,-1.40, 0.44,None, False,True,'2B')
_e(28,'Ni','Nickel'      ,58.693,4,10,'d',1728.0,3186.0, 8.908,13.4, 90.9, 450,
    200., 76., 180.0,0.310, 638, 1.91,10,(2,3), 6.99,5.15,124,'FCC','ferro',0.60,627,
    4.49,False, 2.08,-1.30, 0.77,None, False,True,'1')
_e(29,'Cu','Copper'      ,63.546,4,11,'d',1358.0,2835.0, 8.960,16.5,401.0, 343,
    130., 48.3,140.0,0.340, 343, 1.90,11,(1,2), 1.678,4.65,128,'FCC','dia',None,None,
    3.78,False, 1.79,-2.80, 0.13,None, False,False,None)
_e(30,'Zn','Zinc'        ,65.380,4,12,'d',692.7,1180.0,  7.134,30.2,116.0, 327,
    108., 43.4, 70.5,0.249, 412, 1.65,12,(2,), 5.96, 4.33,134,'HCP','dia',None,None,
    1.11,False, 0.99,None, None,None, False,False,None)

_e(31,'Ga','Gallium'     ,69.723,4,13,'p',302.9,2477.0,  5.907,18.0, 40.6, 240,
     9.8,  3.0, 58.1,0.430,  60, 1.81,3,(3,), 27.0, 4.32,135,'ortho','dia',None,None,
    2.91,False, 0.71,None, None,None, False,False,None)
_e(32,'Ge','Germanium'   ,72.630,4,14,'p',1211.0,3106.0, 5.323, 5.75,60.2, 374,
    103., 41.3, 75.8,0.260,None, 2.01,4,(4,), 46e4,5.0,122,'diamond','dia',None,None,
    2.20,False, 1.00,None, None,None, False,False,None)
_e(33,'As','Arsenic'     ,74.922,4,15,'p',1090.0, 887.0, 5.727,None, 50.2,None,
     8.0,None, 22.0,None,None, 2.18,5,(-3,3,5),33e4,3.75,120,'rhomb','dia',None,None,
    4.30,False, None,None, None,None, False,True,'1')
_e(34,'Se','Selenium'    ,78.971,4,16,'p',494.2, 958.0,  4.819,None,  0.52,  90,
    10.0,None,  8.3,0.330,None, 2.55,6,(-2,4,6),None,5.90,119,'hex','dia',None,None,
    11.7,False, None,None, None,None, False,False,'2A')
_e(35,'Br','Bromine'     ,79.904,4,17,'p',265.8, 332.0,  3.120,None,  0.122,None,
    None,None,None,None,None, 2.96,7,(-1,1,3,5),None,None,114,None,'dia',None,None,
    6.90,False, None,None, None,None, False,False,None)
_e(36,'Kr','Krypton'     ,83.798,4,18,'p',115.8, 119.9, 0.00375,None,0.0095, 72,
    None,None,None,None,None, None,0,(),  None,None, 88,None,'dia',None,None,
    25.0,False, None,None, None,None, False,False,None)

_e(37,'Rb','Rubidium'    ,85.468,5, 1,'s',312.5, 961.0, 1.532,90.0, 58.2,  56,
    2.35, 0.9,  2.5,0.290,None, 0.82,1,(1,), 12.5,2.16,265,'BCC','para',None,None,
    0.38,False, 0.09,None, None,None, False,False,None)
_e(38,'Sr','Strontium'   ,87.620,5, 2,'s',1050.0,1655.0, 2.640,22.5, 35.4, 147,
    15.7, 6.0, 12.4,0.280,None, 0.95,2,(2,), 23.0,2.59,215,'FCC','para',None,None,
    1.28,False, 0.41,None, None,None, False,False,None)
_e(39,'Y' ,'Yttrium'     ,88.906,5, 3,'d',1795.0,3618.0, 4.472,10.6, 17.2, 280,
    63.5,25.6, 41.2,0.243,None, 1.22,3,(3,), 59.6,3.10,180,'HCP','para',None,None,
    1.28,False, 1.08,None, None,None, False,False,None)
_e(40,'Zr','Zirconium'   ,91.224,5, 4,'d',2128.0,4682.0, 6.520, 5.7, 22.7, 291,
    68.0,33.0, 94.9,0.330, 903, 1.33,4,(4,), 42.1,4.05,160,'HCP','para',None,None,
    0.185,False, 1.92,None, 0.44,0.61, False,False,None)
_e(41,'Nb','Niobium'     ,92.906,5, 5,'d',2750.0,5017.0, 8.570, 7.3, 53.7, 275,
    105., 37.5,170.0,0.400,1320, 1.60,5,(3,5), 15.2,4.30,146,'BCC','para',None,None,
    1.15,False, 2.66,-2.00, 1.27,9.26, False,False,None)
_e(42,'Mo','Molybdenum'  ,95.960,5, 6,'d',2896.0,4912.0,10.280, 4.8,138.0, 450,
    329.,126., 230.0,0.310,1530, 2.16,6,(4,6),  5.34,4.60,139,'BCC','para',None,None,
    2.48,False, 2.91,-1.80, 0.41,0.92, False,False,None)
_e(43,'Tc','Technetium'  ,98.000,5, 7,'d',2430.0,4538.0,11.500,None, 50.6, 453,
    None,None,None,None,None, 1.90,7,(4,7), 20.0,None,136,'HCP','para',None,None,
    20.0,True,  2.20,-1.70, None,7.80, False,False,None)
_e(44,'Ru','Ruthenium'   ,101.07,5, 8,'d',2607.0,4423.0,12.370, 6.40,117.0, 600,
    447.,173., 321.0,0.270,None, 2.20,8,(2,3,4),7.60,4.71,134,'HCP','para',None,None,
    2.56,False, 3.05,-1.20, 0.66,0.49, False,False,None)
_e(45,'Rh','Rhodium'     ,102.91,5, 9,'d',2237.0,3968.0,12.410, 8.2,150.0, 480,
    275.,150., 270.0,0.264,None, 2.28,9,(3,),  4.33,4.98,134,'FCC','para',None,None,
    145.,False, 2.66,-1.50, 0.46,None, False,False,None)
_e(46,'Pd','Palladium'   ,106.42,5,10,'d',1828.0,3236.0,12.020,11.8, 71.8, 274,
    121., 43.6,180.0,0.390, 461, 2.20,10,(2,4),10.8, 5.12,137,'FCC','para',None,None,
    6.90,False, 2.00,-1.80, 0.66,None, False,False,None)
_e(47,'Ag','Silver'      ,107.87,5,11,'d',1235.0,2435.0,10.490,18.9,429.0, 225,
    83.0,30.3,100.0,0.370, 251, 1.93,11,(1,), 1.63, 4.26,144,'FCC','dia',None,None,
    63.3,False, 1.25,-3.70, 0.14,None, False,False,None)
_e(48,'Cd','Cadmium'     ,112.41,5,12,'d',594.2,1040.0,  8.650,30.8, 96.9, 209,
    63.0,24.0, 62.0,0.300, 203, 1.69,12,(2,), 7.27,4.22,151,'HCP','dia',None,None,
    2520.,False, 0.78,None, None,0.52, True,True,'1')
_e(49,'In','Indium'      ,114.82,5,13,'p',429.8,2345.0,  7.310,32.1, 81.8, 108,
    10.6, 4.0, 40.2,0.449,  9.0, 1.78,3,(3,), 8.37,4.12,167,'tet','dia',None,None,
    193.,False, 0.63,None, 0.81,3.40, False,False,None)
_e(50,'Sn','Tin'         ,118.71,5,14,'p',505.1,2875.0,  7.265,22.0, 66.8, 200,
    49.9,18.4, 58.2,0.357, 103, 1.96,4,(2,4),11.5, 4.42,158,'tet','dia',None,None,
    0.626,False, 0.64,None, 0.72,3.72, False,False,None)
_e(51,'Sb','Antimony'    ,121.76,5,15,'p',903.8,1908.0,  6.697,11.0, 24.4, 211,
    55.0,20.0, 42.0,0.330, 294, 2.05,5,(-3,3,5),39.0,4.55,145,'rhomb','dia',None,None,
    4.91,False, 0.60,None, None,None, False,False,None)
_e(52,'Te','Tellurium'   ,127.60,5,16,'p',722.7,1261.0,  6.240,18.0,  4.35, 152,
    43.0,None, 65.0,None,None, 2.10,6,(-2,4,6),1e5,4.95,140,'hex','dia',None,None,
    4.70,False, None,None, None,None, False,False,'2B')
_e(53,'I' ,'Iodine'      ,126.90,5,17,'p',386.9, 457.6,  4.940,None,  0.449,None,
    None,None,None,None,None, 2.66,7,(-1,1,5,7),None,None,133,'ortho','dia',None,None,
    6.20,False, None,None, None,None, False,False,None)
_e(54,'Xe','Xenon'       ,131.29,5,18,'p',161.4, 165.1, 0.00590,None,0.0057, 64,
    None,None,None,None,None, None,0,(),  None,None,108,None,'dia',None,None,
    23.9,False, None,None, None,None, False,False,None)

_e(55,'Cs','Caesium'     ,132.91,6, 1,'s',301.6, 944.0,  1.930,97.0, 35.9,  38,
    1.69, 0.63, 1.6,0.350,None, 0.79,1,(1,), 20.8,2.14,298,'BCC','para',None,None,
    29.0,False, 0.06,None, None,None, False,False,None)
_e(56,'Ba','Barium'      ,137.33,6, 2,'s',1000.0,2143.0, 3.510,20.6, 18.4, 110,
    12.8, 4.9,  9.6,0.290,None, 0.89,2,(2,), 34.0,2.52,253,'BCC','para',None,None,
    1.10,False, 0.37,None, None,None, False,False,None)
_e(57,'La','Lanthanum'   ,138.91,6,None,'f',1193.0,3737.0, 6.162,12.1, 13.4, 142,
    36.6,14.3, 27.9,0.280, 363, 1.10,3,(3,), 61.4,3.50,195,'hex','para',None,None,
    9.27,False, 1.02,None, 0.81,6.00, False,False,None)
_e(58,'Ce','Cerium'      ,140.12,6,None,'f',1068.0,3716.0, 6.770, 6.3, 11.3, 146,
    33.6,13.5, 21.5,0.244, 270, 1.12,3,(3,4),73.6,2.90,185,'FCC','para',None,None,
    0.630,False, 0.63,None, None,None, False,False,None)
_e(59,'Pr','Praseodymium',140.91,6,None,'f',1208.0,3793.0, 6.773, 6.7, 12.5, 152,
    37.3,14.8, 28.8,0.281, 380, 1.13,3,(3,4),68.0,None,185,'hex','para',3.2,None,
    11.5,False, 0.70,None, None,None, False,False,None)
_e(60,'Nd','Neodymium'   ,144.24,6,None,'f',1297.0,3347.0, 7.008, 9.6, 16.5, 163,
    41.4,16.3, 31.8,0.281, 343, 1.14,3,(3,), 64.3,None,185,'hex','para',3.3,None,
    50.5,False, 0.74,None, None,None, False,False,None)
_e(62,'Sm','Samarium'    ,150.36,6,None,'f',1345.0,2067.0, 7.353,12.7, 13.3, 169,
    49.7,19.5, 37.8,0.274, 412, 1.17,3,(2,3),104.,None,185,'hex','para',None,None,
    5922.,False, 0.75,None, None,None, False,False,None)
_e(63,'Eu','Europium'    ,151.96,6,None,'f',1095.0,1800.0, 5.244,35.0, 13.9, 127,
    18.2, 7.9, 8.3,0.152,None, 1.20,3,(2,3),91.0,None,185,'BCC','para',None,None,
    4500.,False, 0.36,None, None,None, False,False,None)
_e(64,'Gd','Gadolinium'  ,157.25,6,None,'f',1585.0,3546.0, 7.901, 9.4, 10.6, 169,
    54.8,21.8, 37.9,0.259, 570, 1.20,3,(3,), 131.,None,180,'HCP','ferro',7.63,292,
    49700.,False, 0.63,None, None,None, False,False,None)
_e(65,'Tb','Terbium'     ,158.93,6,None,'f',1629.0,3503.0, 8.230, 10.3,11.1, 177,
    55.7,22.1, 38.7,0.261, 677, 1.20,3,(3,4),114.,None,175,'HCP','ferro',9.0,222,
    23.4,False, 0.69,None, None,None, False,False,None)
_e(66,'Dy','Dysprosium'  ,162.50,6,None,'f',1680.0,2840.0, 8.551,  9.9,10.7, 183,
    61.4,24.7, 40.5,0.247, None, 1.22,3,(3,), 994.,None,175,'HCP','ferro',10.0,88,
    994.,False, 0.67,None, None,None, False,False,None)
_e(67,'Ho','Holmium'     ,164.93,6,None,'f',1734.0,2993.0, 8.795,11.2,16.2, 191,
    64.8,26.3, 40.2,0.231, None, 1.23,3,(3,), 81.0,None,175,'HCP','para',10.6,None,
    64.7,False, 0.69,None, None,None, False,False,None)
_e(68,'Er','Erbium'      ,167.26,6,None,'f',1802.0,3141.0, 9.066,12.2,14.5, 188,
    69.9,28.3, 44.4,0.237, None, 1.24,3,(3,), 86.0,None,175,'HCP','para',9.0,None,
    159.,False, 0.73,None, None,None, False,False,None)
_e(69,'Tm','Thulium'     ,168.93,6,None,'f',1818.0,2223.0, 9.321,13.3,16.9, 200,
    74.0,30.5, 44.5,0.213, None, 1.25,3,(3,), 79.0,None,175,'HCP','para',7.0,None,
    100.,False, 0.71,None, None,None, False,False,None)
_e(70,'Yb','Ytterbium'   ,173.04,6,None,'f',1097.0,1469.0, 6.570,26.3,38.5, 118,
    23.9,  9.9, 30.5,0.208, None, 1.10,3,(2,3), 25.0,None,175,'FCC','para',None,None,
    34.8,False, 0.38,None, None,None, False,False,None)
_e(71,'Lu','Lutetium'    ,174.97,6,None,'f',1936.0,3675.0, 9.841, 9.9,16.4, 183,
    68.6,27.2, 47.6,0.261, None, 1.27,3,(3,), 57.0,None,175,'HCP','para',None,None,
    74.0,False, 0.89,None, None,None, False,False,None)

_e(72,'Hf','Hafnium'     ,178.49,6, 4,'d',2506.0,4876.0,13.310, 5.9, 23.0, 252,
    78.0,30.0,109.0,0.370,1760, 1.30,4,(4,), 35.0,3.90,156,'HCP','para',None,None,
    102.,False, 2.15,None, None,None, False,False,None)
_e(73,'Ta','Tantalum'    ,180.95,6, 5,'d',3290.0,5731.0,16.650, 6.3, 57.5, 240,
    186., 69.2,200.0,0.342, 873, 1.50,5,(5,), 12.4,4.25,146,'BCC','para',None,None,
    20.6,False, 3.08,-2.10, 0.69,4.48, False,False,None)
_e(74,'W' ,'Tungsten'    ,183.84,6, 6,'d',3695.0,5828.0,19.250, 4.5,173.0, 400,
    411.,161., 310.0,0.280,3430, 2.36,6,(4,6),  5.56,4.55,139,'BCC','para',None,None,
    18.3,False, 3.26,-1.60, 0.28,None, False,False,None)
_e(75,'Re','Rhenium'     ,186.21,6, 7,'d',3459.0,5869.0,21.020, 6.2, 47.9, 416,
    460.,178., 370.0,0.300,2450, 1.90,7,(4,7), 21.0,4.96,137,'HCP','para',None,None,
    90.0,False, 3.63,-1.70, 0.46,1.70, False,False,None)
_e(76,'Os','Osmium'      ,190.23,6, 8,'d',3306.0,5285.0,22.590, 5.1, 87.6, 500,
    560.,222., 411.0,0.250,4000, 2.20,8,(4,), 15.3,5.93,135,'HCP','para',None,None,
    16.0,False, 4.00,-1.30, 0.39,0.66, False,False,None)
_e(77,'Ir','Iridium'     ,192.22,6, 9,'d',2719.0,4701.0,22.560, 6.4,147.0, 420,
    528.,210., 383.0,0.260,1760, 2.20,9,(3,4),  5.30,5.67,136,'FCC','para',None,None,
    425.,False, 3.22,-1.60, 0.39,None, False,False,None)
_e(78,'Pt','Platinum'    ,195.08,6,10,'d',1768.0,4098.0,21.450, 8.8, 71.6, 240,
    168., 61.0,278.0,0.380, 549, 2.28,10,(2,4),10.6,5.65,139,'FCC','para',None,None,
    10.3,False, 2.48,-2.30, 0.66,None, False,False,None)
_e(79,'Au','Gold'        ,196.97,6,11,'d',1337.0,3129.0,19.320,14.2,318.0, 165,
    79.0,27.0,220.0,0.440, 216, 2.54,11,(1,3),  2.44,5.10,144,'FCC','dia',None,None,
    98.7,False, 1.54,-3.30, 0.13,None, False,False,None)
_e(80,'Hg','Mercury'     ,200.59,6,12,'d',234.3, 629.9,13.530,60.4,  8.34, 100,
    None,None, 25.0,None,None, 2.00,12,(1,2),94.1,4.49,150,None,'dia',None,None,
    2.00,False, None,None, None,None, True,True,'1')
_e(81,'Tl','Thallium'    ,204.38,6,13,'p',577.0,1746.0, 11.850,29.9, 46.1,  79,
     8.0, 2.8, 43.0,0.450,  20, 2.04,3,(1,3),18.0,3.84,170,'HCP','dia',None,None,
     3.40,False, 0.58,None, None,None, True,True,None)
_e(82,'Pb','Lead'        ,207.20,6,14,'p',600.6,2022.0, 11.340,28.9, 35.3, 105,
    13.8, 5.6, 45.8,0.440,  38, 2.33,4,(2,4),19.0,4.25,175,'FCC','dia',None,None,
    0.171,False, 0.60,None, 1.55,7.20, True,True,'2A')
_e(83,'Bi','Bismuth'     ,208.98,6,15,'p',544.6,1837.0,  9.780,13.4,  7.97, 119,
    31.0,12.0, 31.0,0.330,  94, 2.02,5,(3,5),107.,4.22,155,'rhomb','dia',None,None,
    0.034,False, 0.53,None, None,None, False,False,None)

_e(88,'Ra','Radium'      ,226.03,7, 2,'s',973.0,1413.0,  5.000,None, 18.6,None,
    None,None,None,None,None, 0.90,2,(2,),None,None,221,'BCC','para',None,None,
    12.8,True,  None,None, None,None, False,False,None)
_e(90,'Th','Thorium'     ,232.04,7,None,'f',2023.0,5061.0,11.720,11.0, 54.0, 163,
    79.0,31.0, 54.0,0.270, 350, 1.30,3,(4,),  7.35,3.40,206,'FCC','para',None,None,
    7.37,True,  1.20,None, None,None, False,False,None)
_e(92,'U' ,'Uranium'     ,238.03,7,None,'f',1405.0,4404.0,19.050,13.9, 27.5, 207,
    208.,111., 100.0,0.230,2000, 1.38,3,(4,6), 29.0,3.63,196,'ortho','para',None,None,
    7.57,True,  1.50,None, None,None, False,False,None)
_e(93,'Np','Neptunium'   ,237.05,7,None,'f',912.0,4175.0, 20.450, None,6.30,None,
    None,None,None,None,None, 1.36,3,(4,5,6),None,None,190,'ortho','para',None,None,
    180.,True,  None,None, None,None, False,False,None)
_e(94,'Pu','Plutonium'   ,244.06,7,None,'f',912.5,3501.0,19.840,54.0,  6.74,None,
    96.0,None, 54.0,None,None, 1.28,3,(3,4,5,6),14.7,None,187,'mono','para',None,None,
    1017.,True, None,None, None,None, False,False,None)
_e(95,'Am','Americium'   ,243.06,7,None,'f',1449.0,2880.0,13.670, None,10.0,None,
    None,None,None,None,None, 1.30,3,(3,4,5,6),3.26,None,180,'hex','para',None,None,
    75.3,True,  None,None, None,None, False,False,None)


def get(symbol_or_Z: str) -> Element:
    el = _DB.get(str(symbol_or_Z))
    if el is None:
        raise KeyError(f"Element '{symbol_or_Z}' not in database. "
                       f"Use available() to list supported elements.")
    return el

def available() -> list:
    return sorted(k for k in _DB if not k.isdigit())

def validate_composition(comp: dict, tol: float = 0.005) -> dict:
    if not comp:
        raise ValueError("Empty composition")
    for s in comp:
        if str(s) not in _DB:
            raise KeyError(f"Unknown element '{s}'. Available: {available()}")
        if comp[s] < 0:
            raise ValueError(f"Negative fraction for '{s}': {comp[s]}")
    total = sum(comp.values())
    if total <= 0:
        raise ValueError("All fractions are zero")
    if abs(total - 1.0) > tol:
        raise ValueError(
            f"Composition sums to {total:.6f}, not 1.0 ± {tol}. "
            f"Elements: {list(comp.keys())}. "
            f"Adjust fractions so they sum exactly to 1.0.")
    return {s: v / total for s, v in comp.items() if v > 1e-8}

ELEMENTS = _DB
