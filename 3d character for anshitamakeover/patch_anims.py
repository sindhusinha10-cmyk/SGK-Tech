import io, sys

P = '/home/user/index-expressions.html'
s = io.open(P, encoding='utf-8').read()
orig = len(s)
log = []

def rep(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        print('FAIL[' + label + '] count=' + str(n))
        sys.exit(1)
    s = s.replace(old, new)
    log.append('ok ' + label)

# ===========================================================================
# 1. Constructor: channels for stance, locomotion and the new reactions
# ===========================================================================
rep(u"        this.reactions = ['tickle', 'shy', 'bounce'];\n",
    u"        this.reactions = ['tickle', 'shy', 'bounce', 'spin', 'startle', 'pose'];\n"
    u"        this.stanceY = 0; this.stepLift = 0; this.stepX = 0;\n"
    u"        this.hipBase = 0; this.wiggle = 0; this.spin = 0; this.armSwingX = 0;\n"
    u"        this._stanceHip = 0; this._stanceArmX = 0;\n"
    u"        this.stepElapsed = 0; this.stepTimer = 4 + Math.random() * 6;\n",
    'ctor-fields')

# ===========================================================================
# 2. update(): continuous locomotion + the periodic step
#    Everything writes through properties because update() rewrites the
#    transforms every frame -- anything tweened directly gets wiped.
# ===========================================================================
rep(u"        this.root.position.y = FLOOR_Y + Math.sin(time * 1.35 + this.phase) * .012 + this.jump;\n",
    u"        this.root.position.y = FLOOR_Y + Math.sin(time * 1.35 + this.phase) * .012 + this.jump + this.stanceY + this.stepLift;\n"
    u"        /* Locomotion: slow weight shift, gentle body turn, slight drift and\n"
    u"           hanging arms that sway -- nobody is a static mannequin between poses. */\n"
    u"        const st = time * .55 + this.phase;\n"
    u"        this.root.rotation.z = this.hipBase + this.wiggle + Math.sin(st * 1.15) * .012;\n"
    u"        this.root.rotation.y = this.spin + Math.sin(st * .42) * .035;\n"
    u"        this.root.position.x = this.stepX + Math.sin(st * .55) * .010;\n"
    u"        [this.armL, this.armR].forEach((a, i) => { if (a && !a.isWing) a.shoulder.rotation.x = this.armSwingX + Math.sin(st * 1.1 + i * 1.6) * .022; });\n",
    'update-locomotion')

rep(u"        this.tickers.forEach(fn => fn(time, dt));",
    u"        this.stepElapsed += dt;\n"
    u"        if (this.stepElapsed >= this.stepTimer) {\n"
    u"          this.stepElapsed = 0; this.stepTimer = 5.5 + Math.random() * 6.5;\n"
    u"          if (!this._reactBusy) this.twoStep();\n"
    u"        }\n"
    u"        this.tickers.forEach(fn => fn(time, dt));",
    'update-steptimer')

# ===========================================================================
# 3. MOODS: five new expressions, each with a whole-body stance
# ===========================================================================
ms = s.index(u"    const MOODS = {")
me = s.index(u"    };\n", ms) + len(u"    };\n")
new_moods = u"""    /* STANCE is how they HOLD themselves; the face alone is only half an
       expression. lean = pitch, stanceY = height, armX = arms forward/back,
       hip = hip cocked, squash = body volume. */
    const POSES = {
      neutral: { lean:  0,     stanceY:  0,     armX:   0,   hip:  0,     squash: 1     },
      slump:   { lean:  .055,  stanceY: -.035,  armX: -.10,  hip:  .02,   squash: .965  },
      wait:    { lean: -.015,  stanceY: -.012,  armX:  .04,  hip:  .11,   squash: 1.010 },
      offer:   { lean: -.070,  stanceY:  .022,  armX:  .58,  hip: -.03,   squash: 1.025 },
      proud:   { lean: -.035,  stanceY:  .012,  armX:  .12,  hip: -.075,  squash: 1.030 },
      startle: { lean:  .070,  stanceY:  .026,  armX: -.28,  hip:  0,     squash: .975  }
    };
    const MOODS = {
      welcome:  { left: -1.58, right: 1.58, leftElbow: -.48, rightElbow: -.48,  headZ: 0,     headY: 0,    headX:  0,    brow: .55, browTilt:  0,    eye: 1.00, mouthCurve:  1.00, mouthOpen: 0,    pose:'neutral' },
      happy:    { left: -2.25, right: 2.25, leftElbow: -.35, rightElbow: -.35,  headZ: -.035, headY: 0,    headX:  0,    brow: .95, browTilt: -.22, eye: .42,  mouthCurve:  1.70, mouthOpen: .60, pose:'proud'   },
      thinking: { left: -1.05, right: 2.72, leftElbow: -.35, rightElbow: -1.25, headZ: -.12,  headY: .12,  headX:  .03,  brow: .30, browTilt:  .60, eye: .78,  mouthCurve:  .30,  mouthOpen: 0,    pose:'neutral' },
      hesitant: { left: -.92,  right: .92,  leftElbow: -.2,  rightElbow: -.2,   headZ: .1,    headY: -.08, headX:  .045, brow: -.38, browTilt: -.48, eye: 1.14, mouthCurve: -.40,  mouthOpen: .18, pose:'slump'   },
      sad:      { left: -.48,  right: .48,  leftElbow: -.10, rightElbow: -.10,  headZ: .02,   headY: .05,  headX:  .12,  brow: -.95, browTilt: .35,  eye: .55,  mouthCurve: -1.20, mouthOpen: .06, pose:'slump'   },
      waiting:  { left: -1.15, right: 1.15, leftElbow: -.62, rightElbow: -.62,  headZ: .20,   headY: .06,  headX:  .02,  brow: .20, browTilt:  .70, eye: .95,  mouthCurve:  .12,  mouthOpen: .05, pose:'wait'    },
      coupon:   { left: -2.45, right: 2.45, leftElbow: -.85, rightElbow: -.85,  headZ: -.04,  headY: 0,    headX: -.05,  brow: .80, browTilt: -.10, eye: 1.15, mouthCurve:  1.55, mouthOpen: .30, pose:'offer'   },
      wink:     { left: -1.90, right: 1.90, leftElbow: -.50, rightElbow: -.50,  headZ: -.06,  headY: .04,  headX: -.02,  brow: .70, browTilt:  .15, eye: 1.00, mouthCurve:  1.25, mouthOpen: .10, pose:'proud', wink:true },
      surprised:{ left: -2.60, right: 2.60, leftElbow: -1.1, rightElbow: -1.1,  headZ: 0,     headY: 0,    headX: -.04,  brow: 1.15, browTilt: 0,    eye: 1.25, mouthCurve:  .20,  mouthOpen: .55, pose:'startle' }
    };
"""
s = s[:ms] + new_moods + s[me:]
log.append('ok moods-poses (' + str(me - ms) + ' -> ' + str(len(new_moods)) + ')')

# ===========================================================================
# 4. eyePair: wink (one eye only)
# ===========================================================================
rep(u"""        mood(value) {
          const v = (typeof value === 'number') ? value : (value ? .9 : 1);
          api.moodValue = v;
          eyes.forEach(e => {
            if (G) G.to(e.eye.scale, { y: v, duration: .4, ease: 'power2.out', overwrite: true });
            else e.eye.scale.y = v;
          });
        }""",
    u"""        mood(value) {
          const v = (typeof value === 'number') ? value : (value ? .9 : 1);
          api.moodValue = v;
          eyes.forEach(e => {
            if (G) G.to(e.eye.scale, { y: v, duration: .4, ease: 'power2.out', overwrite: true });
            else e.eye.scale.y = v;
          });
        },
        /* One eye only. Reopens to the CURRENT mood so a wink does not wipe
           the squint the expression just set. */
        wink(side) {
          const e = eyes[side < 0 ? 0 : 1];
          if (!e || !G) return;
          G.timeline()
            .to(e.eye.scale, { y: .10, duration: .14, ease: 'power2.in', overwrite: true }, 0)
            .to(e.eye.scale, { y: api.moodValue, duration: .24, ease: 'power2.out' }, .62);
        }""",
    'eyes-wink')

# ===========================================================================
# 5. setEmotion: apply the stance and the wink
# ===========================================================================
rep(u"        this.headTarget.x = name === 'hesitant' ? .045 : 0;",
    u"        this.headTarget.x = pose.headX !== undefined ? pose.headX : 0;",
    'headx')

rep(u"        /* brows are the strongest expression cue and were previously static */",
    u"""        /* Whole-body stance: the pose they hold, not just the face. */
        const stance = POSES[pose.pose] || POSES.neutral;
        this._stanceHip = stance.hip; this._stanceArmX = stance.armX;
        if (G) {
          G.to(this, { stanceY: stance.stanceY, hipBase: stance.hip, duration: .6, ease: 'power2.out' });
          G.to(this.root.rotation, { x: stance.lean, duration: .6, ease: 'power2.out' });
          G.to(this, { squash: stance.squash, duration: .6, ease: 'power2.out' });
        } else {
          this.stanceY = stance.stanceY; this.hipBase = stance.hip;
          this.root.rotation.x = stance.lean; this.squash = stance.squash;
        }
        this.armSwingX = stance.armX;
        /* brows are the strongest expression cue and were previously static */""",
    'setemotion-stance')

rep(u"        if (this.eyes) this.eyes.mood(pose.eye);",
    u"        if (this.eyes) this.eyes.mood(pose.eye);\n"
    u"        if (pose.wink && this.eyes && this.eyes.wink) this.eyes.wink(1);",
    'setemotion-wink')

# ===========================================================================
# 6. Existing reactions: wiggle through the property, not root.rotation.z
#    (update() now owns root.rotation.z)
# ===========================================================================
rep(u"        tl.to(this.root.rotation, { z: .085, duration: .085, repeat: 7, yoyo: true, ease: 'sine.inOut' }, 0)",
    u"        tl.to(this, { wiggle: .085, duration: .085, repeat: 7, yoyo: true, ease: 'sine.inOut' }, 0)",
    'tickle-wiggle-1')
rep(u"          .to(this.root.rotation, { z: 0, duration: .3, ease: 'power2.out' }, .74)",
    u"          .to(this, { wiggle: 0, duration: .3, ease: 'power2.out' }, .74)",
    'tickle-wiggle-2')
rep(u"            .to(this.root.rotation,{z:-.05,duration:.12,repeat:5,yoyo:true,ease:'sine.inOut'},0)",
    u"            .to(this,{wiggle:-.05,duration:.12,repeat:5,yoyo:true,ease:'sine.inOut'},0)",
    'shyfly-wiggle-1')
rep(u"            .to(this.root.rotation,{z:0,duration:.3,ease:'power2.out'},1.05);",
    u"            .to(this,{wiggle:0,duration:.3,ease:'power2.out'},1.05);",
    'shyfly-wiggle-2')

# ===========================================================================
# 7. New reactions: twoStep (movement), spin, startle, pose
# ===========================================================================
NEW_REACTIONS = u"""      /* MOVEMENT: a little two-step shuffle so they shift their weight and
         take a step instead of standing frozen. stepLift/stepX are properties
         because update() rewrites root.position every frame. */
      twoStep() {
        if (!G) return;
        const dir = Math.random() < .5 ? -1 : 1;
        const d = .055 + Math.random() * .05;
        G.timeline()
          .to(this, { stepX: dir * d, duration: .32, ease: 'power2.inOut' }, 0)
          .to(this, { stepLift: .024, duration: .16, ease: 'power2.out' }, 0)
          .to(this, { stepLift: 0, duration: .22, ease: 'power2.in' }, .16)
          .to(this, { stepX: dir * d * .3, duration: .3, ease: 'power2.inOut' }, .34)
          .to(this, { stepLift: .02, duration: .15, ease: 'power2.out' }, .5)
          .to(this, { stepLift: 0, duration: .22, ease: 'power2.in' }, .65)
          .to(this, { stepX: 0, duration: .55, ease: 'power2.inOut' }, .85);
      }
      react_spin() {
        const prev = this.emotion, y0 = this.spin || 0;
        if (this.eyes) this.eyes.mood(.45);
        if (this.mouth) this.mouth.setMood(1.5, .3, .15);
        if (this.brows) this.brows.set(.85, 0);
        if (!G) { window.setTimeout(() => this.setEmotion(prev, false), 700); return .8; }
        const tl = G.timeline({ onComplete: () => { this.spin = y0; this.setEmotion(prev, false); } });
        tl.to(this, { spin: y0 + Math.PI * 2, duration: .85, ease: 'power2.inOut' }, 0)
          .to(this, { jump: .12, duration: .22, ease: 'power2.out' }, .1)
          .to(this, { jump: 0, duration: .3, ease: 'power2.out' }, .32);
        this.flutter(tl, -.8, 1);
        return 1.0;
      }
      react_startle() {
        const prev = this.emotion;
        if (this.eyes) this.eyes.mood(1.3);
        if (this.mouth) this.mouth.setMood(.2, .55, .12);
        if (this.brows) this.brows.set(1.1, 0);
        if (!G) { window.setTimeout(() => this.setEmotion(prev, false), 800); return .9; }
        const tl = G.timeline({ onComplete: () => this.setEmotion(prev, false) });
        tl.to(this, { stepLift: .09, duration: .13, ease: 'power2.out' }, 0)
          .to(this, { stepLift: 0, duration: .32, ease: 'bounce.out' }, .13)
          .to(this, { squash: .92, duration: .1, ease: 'power2.out' }, 0)
          .to(this, { squash: 1, duration: .5, ease: 'elastic.out' }, .18)
          .to(this, { wiggle: .07, duration: .07, repeat: 5, yoyo: true, ease: 'sine.inOut' }, 0)
          .to(this, { wiggle: 0, duration: .25, ease: 'power2.out' }, .5);
        this.flutter(tl, -1.15, 3);
        return 1.0;
      }
      react_pose() {
        const prev = this.emotion, gx = this.gazeTarget.x;
        if (this.eyes) this.eyes.mood(.62);
        if (this.mouth) this.mouth.setMood(1.25, .08, .3);
        if (this.brows) this.brows.set(.6, .1);
        if (!G) { window.setTimeout(() => this.setEmotion(prev, false), 1200); return 1.3; }
        const tl = G.timeline({ onComplete: () => { G.to(this.gazeTarget, { x: gx, duration: .5 }); this.setEmotion(prev, false); } });
        tl.to(this, { hipBase: -.13, duration: .4, ease: 'power2.out' }, 0)
          .to(this.headTarget, { x: -.07, y: .18, duration: .45, ease: 'power2.out' }, 0)
          .to(this.gazeTarget, { x: .5, duration: .45, ease: 'power2.out' }, 0)
          .to(this, { armSwingX: .24, duration: .4, ease: 'power2.out' }, 0)
          .to(this, { hipBase: this._stanceHip, duration: .5, ease: 'power2.inOut' }, 1.15)
          .to(this.headTarget, { x: 0, y: 0, duration: .5, ease: 'power2.inOut' }, 1.15)
          .to(this.gazeTarget, { x: gx, duration: .5, ease: 'power2.inOut' }, 1.15)
          .to(this, { armSwingX: this._stanceArmX, duration: .5, ease: 'power2.inOut' }, 1.15);
        return 1.75;
      }
      setEmotion(name, announce = true) {"""

rep(u"      setEmotion(name, announce = true) {", NEW_REACTIONS, 'new-reactions')

# ===========================================================================
# 8. Pip's pool gets the spin too
# ===========================================================================
rep(u"        this.reactions=['shyFly','tickle'];",
    u"        this.reactions=['shyFly','tickle','spin','startle'];",
    'pip-pool')

# ===========================================================================
# 9. Dialogue for the five new moods
# ===========================================================================
rep(u"""        Tara:'Tara folds her hands and breathes with you.', Gia:'Gia softens her glow and listens.', Pip:'Pip settles close by. The choice can wait.'
      }
    };""",
    u"""        Tara:'Tara folds her hands and breathes with you.', Gia:'Gia softens her glow and listens.', Pip:'Pip settles close by. The choice can wait.'
      },
      sad: {
        Asha:'“Oh… that slot is gone. My heart sinks a little too.”', Mochi:'Mochi’s ears droop. A small cloud has passed by.',
        Noor:'“That shade is finished. I am so sorry, truly.”', Tara:'Tara lowers her eyes. “The season moved on without us.”',
        Gia:'Gia dims her crystals. “Not this time, sadly.”', Pip:'Pip’s crest flattens and the sparkle dims.'
      },
      waiting: {
        Asha:'“Shall I hold this look for you? No rush at all.”', Mochi:'Mochi waits, nose twitching, one ear half-cocked.',
        Noor:'“Take your time, darling. I will keep the brush warm.”', Tara:'Tara waits softly, jasmine steady in her hands.',
        Gia:'Gia tilts her head. “Still deciding? I have all day.”', Pip:'Pip hops once, then waits, head tilted.'
      },
      coupon: {
        Asha:'“For you — ten percent on the bridal package today.”', Mochi:'Mochi presents a tiny velvet coupon with both paws.',
        Noor:'“A little gift: a complimentary touch-up, on the house.”', Tara:'Tara offers a jasmine-wrapped coupon, smiling.',
        Gia:'“Your first glow-up session — fifteen percent off.”', Pip:'Pip holds up a shimmering coupon in one wing.'
      },
      wink: {
        Asha:'Asha winks. “Trust me, it will be stunning.”', Mochi:'Mochi winks one bright eye and flicks an ear.',
        Noor:'Noor winks. “That is the couturier’s promise.”', Tara:'Tara winks, and the jasmine seems to glow.',
        Gia:'Gia winks. “A little secret between us.”', Pip:'Pip winks a glossy eye, crest a-bounce.'
      },
      surprised: {
        Asha:'“Oh! What a bold, beautiful choice.”', Mochi:'Mochi’s ears shoot straight up in surprise.',
        Noor:'“Mon dieu — I did not see that coming!”', Tara:'Tara’s eyes widen. “What a wonderful turn.”',
        Gia:'Gia gasps, crystals flashing. “Unexpected. Perfect.”', Pip:'Pip’s crest shoots up with a startled cheep.'
      }
    };""",
    'words-new')

# ===========================================================================
# 10. Dock buttons + scroll safety for 9 buttons
# ===========================================================================
NEW_BUTTONS = u"""    <button class="emotion-button" data-mood="sad" aria-pressed="false" title="Apology, something unavailable">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="12" cy="12" r="8.5"/><path d="M8 15.5c1.8-2 6.2-2 8 0M8.5 9.7h.01M15.5 9.7h.01"/></svg><span>Sorry</span>
    </button>
    <button class="emotion-button" data-mood="waiting" aria-pressed="false" title="Waiting while the guest decides">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></svg><span>Waiting</span>
    </button>
    <button class="emotion-button" data-mood="coupon" aria-pressed="false" title="Offering a coupon">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8.5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v1a2.5 2.5 0 0 0 0 5v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1a2.5 2.5 0 0 0 0-5z"/><path d="M9.5 6.5v11"/></svg><span>Coupon</span>
    </button>
    <button class="emotion-button" data-mood="wink" aria-pressed="false" title="Confident wink">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="12" cy="12" r="8.5"/><path d="M7.4 9.9c.85-.95 2.1-.95 2.95 0M14.2 9.9h.01M8 14c1.8 2.2 6.2 2.2 8 0"/></svg><span>Wink</span>
    </button>
    <button class="emotion-button" data-mood="surprised" aria-pressed="false" title="Delighted surprise">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="12" cy="12" r="8.5"/><path d="M8.5 9.5h.01M15.5 9.5h.01"/><circle cx="12" cy="15" r="1.8"/></svg><span>Surprise</span>
    </button>
"""
rep(u"""      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20s-7.5-4.6-7.5-10A4.2 4.2 0 0 1 12 7a4.2 4.2 0 0 1 7.5 3c0 5.4-7.5 10-7.5 10Z"/><path d="M8.5 12h2M13.5 12h2"/></svg><span>Empathy</span>
    </button>
  </div>""",
    u"""      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20s-7.5-4.6-7.5-10A4.2 4.2 0 0 1 12 7a4.2 4.2 0 0 1 7.5 3c0 5.4-7.5 10-7.5 10Z"/><path d="M8.5 12h2M13.5 12h2"/></svg><span>Empathy</span>
    </button>
""" + NEW_BUTTONS + u"""  </div>""",
    'dock-buttons')

rep(u"#emotionDock { position: fixed; z-index: 20; right: 25px; top: 50%; transform: translateY(-25%); display: flex; flex-direction: column; gap: 8px; }",
    u"#emotionDock { position: fixed; z-index: 20; right: 25px; top: 50%; transform: translateY(-25%); display: flex; flex-direction: column; gap: 8px; max-height: 76vh; overflow-y: auto; }",
    'dock-css')
rep(u"      #emotionDock { top: auto; right: 8px; bottom: 150px; transform: none; gap: 5px; }",
    u"      #emotionDock { top: auto; right: 8px; bottom: 150px; transform: none; gap: 5px; max-height: 44vh; overflow-y: auto; }",
    'dock-css-mobile')

# ===========================================================================
# 11. Auto "waiting" when the guest goes quiet
# ===========================================================================
rep(u"""    function setEmotion(mood) {
      if(!activeCharacter)return;
      activeCharacter.setEmotion(mood);
      document.querySelectorAll('.emotion-button').forEach(button=>{
        const on=button.dataset.mood===mood;button.classList.toggle('active',on);button.setAttribute('aria-pressed',on?'true':'false');
      });
    }""",
    u"""    function setEmotion(mood) {
      if(!activeCharacter)return;
      activeCharacter.setEmotion(mood);
      document.querySelectorAll('.emotion-button').forEach(button=>{
        const on=button.dataset.mood===mood;button.classList.toggle('active',on);button.setAttribute('aria-pressed',on?'true':'false');
      });
      armIdleChat();
    }
    /* If the guest stops interacting, the concierge gently switches to the
       "still deciding" waiting pose on their own. */
    let idleChatTimer=null;
    function armIdleChat(){
      if(idleChatTimer)clearTimeout(idleChatTimer);
      idleChatTimer=window.setTimeout(()=>{
        if(viewMode!=='showcase'||!activeCharacter||switching)return;
        if(activeCharacter.emotion!=='waiting') setEmotion('waiting');
      },15000);
    }""",
    'idle-chat')

rep(u"      canvas.addEventListener('pointerdown',event=>{downX=event.clientX;downY=event.clientY;});",
    u"      canvas.addEventListener('pointerdown',event=>{downX=event.clientX;downY=event.clientY;armIdleChat();});",
    'idle-arm-pointer')

rep(u"        activeCharacter.setEmotion(activeCharacter.emotion,false);",
    u"        activeCharacter.setEmotion(activeCharacter.emotion,false);armIdleChat();",
    'idle-arm-switch')

rep(u"activeCharacter.setEmotion('welcome',false);",
    u"activeCharacter.setEmotion('welcome',false);armIdleChat();",
    'idle-arm-boot')

io.open(P, 'w', encoding='utf-8').write(s)
print('\n'.join(log))
print('WROTE ' + str(len(s)) + ' bytes (was ' + str(orig) + ', delta ' + str(len(s) - orig) + ')')
