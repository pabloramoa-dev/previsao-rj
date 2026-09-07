"""Elenco original RJ em geometria vetorial; interface compatível com o motor."""
from manim import *
import numpy as np

INK = '#122E43'
TEAL = '#007F87'
YELLOW = '#FFD166'


def shape(cls, color, **kw):
    return cls(fill_color=color, fill_opacity=1, stroke_color=INK, stroke_width=5, **kw)


def presenter(name='bira'):
    bia = name == 'bia'
    skin = '#C78359' if bia else '#A96D49'
    shirt = '#F0B94D' if bia else TEAL
    hair_color = '#392D32'
    back_hair = shape(RoundedRectangle, hair_color, width=1.95, height=2.1, corner_radius=.65).move_to([0, 1.2, 0]) if bia else VGroup()
    shoes = VGroup(*[shape(RoundedRectangle, '#F6F2E8', width=.68, height=.3, corner_radius=.12).move_to([x, -2.12, 0]) for x in [-.43, .43]])
    legs = VGroup(*[shape(RoundedRectangle, '#234B67', width=.48, height=1.15, corner_radius=.12).move_to([x, -1.5, 0]) for x in [-.4, .4]])
    body = shape(RoundedRectangle, shirt, width=1.55, height=1.65, corner_radius=.32).move_to([0, -.38, 0])
    neck = shape(RoundedRectangle, skin, width=.47, height=.58, corner_radius=.16).move_to([0, .55, 0])
    head = shape(RoundedRectangle, skin, width=1.72, height=1.9, corner_radius=.67).move_to([0, 1.5, 0])
    ears = VGroup(*[shape(Circle, skin, radius=.18).move_to([x, 1.45, 0]) for x in [-.86, .86]])
    hair = VGroup(*[shape(Circle, hair_color, radius=r).move_to([x, y, 0]) for x, y, r in [(-.57, 2.27, .34), (-.2, 2.42, .4), (.23, 2.41, .37), (.57, 2.22, .3)]])
    if bia:
        hair.add(shape(Circle, hair_color, radius=.45).move_to([.85, 2.33, 0]))
        hair.add(Line([.61,2.44,0],[.88,2.57,0],stroke_color=TEAL,stroke_width=10))
    eyes = []
    brows = []
    for x in [-.34, .34]:
        eye = VGroup(shape(Ellipse, WHITE, width=.35, height=.43).move_to([x,1.55,0]),
                     Dot([x+.025,1.54,0],radius=.085,color=INK), Dot([x+.05,1.58,0],radius=.023,color=WHITE))
        eyes.append(eye)
        brows.append(Line([x-.16,1.92,0],[x+.16,1.95,0],stroke_color=INK,stroke_width=7))
    nose = ArcBetweenPoints([.01,1.42,0],[.13,1.22,0],angle=-.8,stroke_color='#754A38',stroke_width=4)
    mouth = ArcBetweenPoints([-.22,1.04,0],[.22,1.04,0],angle=1,stroke_color=INK,stroke_width=5)
    hands = [shape(Circle, skin, radius=.22).move_to([x,-.73,0]) for x in [-1.05,1.05]]
    arms = [Line([x*.7,.14,0],h.get_center(),stroke_color=skin,stroke_width=24) for x,h in zip([-1,1],hands)]
    logo = Text('RJ', font_size=22, weight=BOLD, color=INK if bia else WHITE).move_to([.28,-.12,0])
    collar = VGroup(Line([-.26,.4,0],[0,.15,0],stroke_color=INK,stroke_width=4),Line([0,.15,0],[.26,.4,0],stroke_color=INK,stroke_width=4))
    group = VGroup(back_hair, legs, shoes, *arms, body, neck, ears, head, hair, *eyes, *brows, nose, mouth, collar, logo, *hands)
    result = dict(grupo=group,cab=head,oe=eyes[0],od=eyes[1],boca=mouth,maoE=hands[0],maoD=hands[1],bracoE=arms[0],bracoD=arms[1],sobE=brows[0],sobD=brows[1])
    result.update(cabeca=head,olho_e=eyes[0],olho_d=eyes[1],mao_e=hands[0],mao_d=hands[1])
    return result


def nuvem(expression='neutra'):
    lobes = VGroup(*[shape(Circle, '#F4FAFD', radius=r).move_to([x,y,0]) for x,y,r in [(-.48,0,.42),(0,.22,.57),(.51,.02,.43)]])
    base = shape(RoundedRectangle, '#F4FAFD', width=1.62,height=.56,corner_radius=.26).move_to([0,-.15,0])
    eyes = VGroup(*[Dot([x,.07,0],radius=.065,color=INK) for x in [-.25,.25]])
    mouth = ArcBetweenPoints([-.15,-.12,0],[.15,-.12,0],angle=1 if expression!='preocupada' else -1,stroke_color=INK,stroke_width=4)
    return VGroup(lobes,base,eyes,mouth)


def backdrop(kind='urbano'):
    bg = Rectangle(width=9,height=16,fill_color='#D7EBEF',fill_opacity=1,stroke_width=0)
    sea = Rectangle(width=9,height=3.4,fill_color='#77BBC9',fill_opacity=1,stroke_width=0).move_to([0,-1.1,0])
    hills = Polygon([-4,0,0],[-2.3,2.1,0],[-.8,.2,0],[1,1.35,0],[3,.1,0],[4,.65,0],[4,-2,0],[-4,-2,0],fill_color='#6A9DA6',fill_opacity=1,stroke_width=0)
    floor = Rectangle(width=9,height=4.1,fill_color='#E8D9B8' if kind=='orla' else '#BBCAD0',fill_opacity=1,stroke_width=0).move_to([0,-5.2,0])
    rail = VGroup(Line([-4,-2.25,0],[4,-2.25,0],color=INK,stroke_width=6),*[Line([x,-2.25,0],[x,-3.15,0],color=INK,stroke_width=5) for x in [-3,-1.5,0,1.5,3]])
    return VGroup(bg,sea,hills,floor,rail)
