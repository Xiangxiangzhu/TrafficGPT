from __future__ import absolute_import
from __future__ import print_function

import os
import sys

import matplotlib

matplotlib.use('Agg')

import sumolib  # noqa
from sumolib.visualization import helpers  # noqa
from sumolib.options import ArgumentParser  # noqa
import matplotlib.pyplot as plt  # noqa


def plot_intersections(target_junction_id, folderpath, args=None) -> str:
    """The main function; parses options and plots"""
    # ---------- build and read options ----------
    ap = ArgumentParser()
    ap.add_argument("-n", "--net", dest="net", category="input", type=ap.net_file, metavar="FILE",
                    required=True, help="Defines the network to read")
    ap.add_argument("-v", "--verbose", dest="verbose", action="store_true",
                    default=False, help="If set, the script says what it's doing")
    ap.add_argument("-w", "--width", dest="width",
                    type=float, default=20, help="Defines the width of the dots")
    ap.add_argument("--color", dest="color", category="visualization",
                    default='r', help="Defines the dot color")
    ap.add_argument("--edge-width", dest="defaultWidth", category="visualization",
                    type=float, default=1, help="Defines the edge width")
    ap.add_argument("--edge-color", dest="defaultColor", category="visualization",
                    default='k', help="Defines the edge color")
    # standard plot options
    helpers.addInteractionOptions(ap)
    helpers.addPlotOptions(ap)
    # parse
    options = ap.parse_args(args=args)

    if options.verbose:
        print("Reading network from '%s'" % options.net)
    net = sumolib.net.readNet(options.net)

    tls_n = {}
    for tid in net._id2tls:
        print("tid has: ", tid)
        t = net._id2tls[tid]
        tls_n[tid] = set()
        for c in t._connections:
            n = c[0].getEdge().getToNode()
            print("tls have connection: ", n)
            tls_n[tid].add(n)

    # all edges
    edge_n = {}
    for eid in net._id2edge:
        # print("edge has: ", eid)
        edge_n[eid] = set()

    # all nodes
    node_n = {}
    for nid in net._id2node:
        # print("node has: ", nid)
        t = net._id2node[nid]
        node_n[nid] = t

    # # TODO: 这段代码冗余过多，需要优化
    def calculate_position_(label_n):
        tlspX_ = []
        tlspY_ = []
        junctionID_ = []
        for tid in label_n:
            if tid in target_junction_id:
                x, y = label_n[tid].getCoord()
                x, y = (sum(coord[0] for coord in label_n[tid].getShape()) / len(label_n[tid].getShape()),
                        sum(coord[1] for coord in label_n[tid].getShape()) / len(label_n[tid].getShape()))
                tlspX_.append(x)
                tlspY_.append(y)
                junctionID_.append(tid)
        return tlspX_, tlspY_, junctionID_

    # todo: need to add swith condition
    tlspX, tlspY, junctionID = calculate_position_(node_n)
    # tlspX, tlspY, junctionID = calculate_position(node_n)

    fig, ax = helpers.openFigure(options)
    ax.set_aspect("equal", None, 'C')
    helpers.plotNet(net, {}, {}, options)
    plt.plot(tlspX, tlspY, options.color, linestyle='',
             marker='o', markersize=options.width)
    for i in range(len(junctionID)):
        plt.text(tlspX[i] * 1.01, tlspY[i] * 1.01, str(junctionID[i]), fontsize=10, color="r", style="italic",
                 weight="light", verticalalignment='center', horizontalalignment='right', rotation=0)  # 给散点加标签

    options.nolegend = True
    fig_path = f'{folderpath}intersections.png'
    fig.savefig(fig_path, dpi=1600)
    helpers.closeFigure(fig, ax, options)

    return fig_path
