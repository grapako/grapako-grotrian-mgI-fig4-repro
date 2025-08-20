# src/grotrian_plotter/plotting.py
import matplotlib.pyplot as plt
import numpy as np


def plot_levels_and_transitions(levels, transitions, outpath=None, show=True, title=''):
    """Plot the levels and transitions. levels: list of dicts (with xstart, energy, label...)."""
    # plotting parameters (kept as in original)
    levelWidth = 0.1
    plt.rcParams["figure.figsize"] = (4.6 * 1.5, 3.46 * 1.5)
    font_size = 10

    fig, ax = plt.subplots()

    temp = []
    for l in levels:
        # draw horizontal level
        ax.plot([l['xstart'] - levelWidth, l['xstart'] + levelWidth],
                [l['energy'], l['energy']], '-0')

        # determine tag text (keeps original mapping)
        if l['energy'] == 0:
            tag = '$3s^2$'
        elif l['energy'] in [6.8275, 6.136555]:
            tag = ''
        elif np.isclose(l['energy'], 5.781276999999999):
            tag = '$3p^2$'
        else:
            # fallback to label parsing similar to original
            try:
                tag = l['label'].split('^')[0] + l['label'].split('_')[0][-1].lower()
            except Exception:
                tag = l['label']

        L = l['label'].split('_')[0][-1]

        # annotation logic preserved
        if (('show_J' in globals() and globals()['show_J'] == 'no') or l['mult'] == '*'):
            ax.annotate(tag, xy=(l['xstart'] + levelWidth, l['energy']), fontsize=font_size)
        elif l['mult'] == 1 or L == 'S':
            ax.annotate(tag + '$_{'+ str(l['j']) + '}$',
                        xy=(l['xstart'] + levelWidth, l['energy']), fontsize=font_size)
        elif isinstance(l['mult'], int) and l['mult'] > 1:
            temp.append([str(l['j']), l['energy']])
            if l['mult'] == len(temp):  # usually 3
                js = ','.join([x[0] for x in temp])
                aver_ener = sum([x[1] for x in temp]) / len([x[1] for x in temp])
                ax.annotate(tag + '$_{'+js+'}$',
                            xy=(l['xstart'] + levelWidth, aver_ener), fontsize=font_size)
                temp = []

    # Manual annotations from original script
    positions = [lv['xstart'] for lv in levels]
    x1, x2 = min(positions) - 0.2, max(positions) + 0.2
    ax.plot([x1, x2], [6.8275, 6.8275], 'blue')
    ax.annotate('$3p^2$', xy=(x2, 6.8275), fontsize=font_size)

    ax.plot([x1, x2], [6.0825, 6.0825], 'green')
    # original placed label at levels[-2]['energy'] - keep similar behavior with safe access
    try:
        y_for_label = levels[-2]['energy']
    except Exception:
        y_for_label = 6.0825
    ax.annotate('nl=9s-20p', xy=(x2, y_for_label), fontsize=font_size)

    # plot transitions as arrows (cyan dotted)
    for t in transitions:
        try:
            i = t['i']; f = t['f']
            ax.arrow(levels[i]['xstart'], levels[i]['energy'],
                     levels[f]['xstart'] - levels[i]['xstart'],
                     levels[f]['energy'] - levels[i]['energy'],
                     head_width=0, head_length=0, linestyle=':', color='cyan')
        except Exception:
            # skip transitions that map out of bounds
            continue

    # xticks and labels
    font_axis_size = 12
    xticks = ['$^3S$','$^3P$','$^3D$','$^3F$','$^3G$','$^3H$','$^3I$','',
              '$^1S$','$^1P$','$^1D$','$^1F$','$^1G$','$^1H$','$^1I$']
    ax.set_xticks([i for i in range(len(xticks))])
    ax.set_xticklabels(xticks)
    ax.set_xlim(-1, 13)
    ax.set_ylabel('Energy ($10^4 \\ cm^{-1}$)', fontsize=font_axis_size)
    ax.tick_params(axis='x', labelsize=font_axis_size)
    plt.tight_layout()

    if outpath:
        fig.savefig(outpath, dpi=200)
        print(f"[INFO] Figure saved to {outpath}")
    if show and not outpath:
        plt.show()
    plt.close(fig)
