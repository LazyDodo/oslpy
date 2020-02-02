import bpy

from .OpcodeBaseTypes import Opcode, Opcode_DS, Opcode_DSS, Opcode_SDD
from .OpcodeBaseTypes import Opcode_DSSS, Opcode_DSI, Opcode_DIS, Opcode_D
from .OpcodeBaseTypes import Opcode_basicMath1, Opcode_basicMath
from .OSOVariable import OSOVariable


def float_range(start, stop, step):
    while start < stop:
        yield start
        start += step


class Opcode_nop(Opcode):
    def __init__(self, OSO, index):
        Opcode.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        pass


class Opcode_assign(Opcode_DS):
    def __init__(self, OSO, index):
        Opcode_DS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        # same datatypes can just be assigned
        # int->float can just be assigned
        if ((self.Destination.dataType == self.Source.dataType) or
                (self.Destination.IsFloat() and self.Source.IsInt())):
            nodeGraph.Assign(self.Destination, self.Source)
        # color/point/vector can be mixed
        elif (self.Destination.IsPointLike() and self.Source.IsPointLike()):
            nodeGraph.Assign(self.Destination, self.Source)
        elif (self.Destination.IsInt() and self.Source.IsFloat()):
            # int->float needs to be floored
            node = nodeGraph.CreateNode('ShaderNodeMath')
            node.SetProperty("operation", "SUBTRACT")
            nodeGraph.AddLink(node, 0, self.Source)
            node.SetProperty("inputs[1].default_value", "0.5")
            node2 = nodeGraph.CreateNode('ShaderNodeMath')
            node2.SetProperty("operation", "ROUND")
            node2.SetProperty("inputs[1].default_value", "0.5")
            nodeGraph.AddNodeLink(node2, 0, node, 0)
            nodeGraph.SetVar(self.Destination, node2, 0)
        elif (self.Destination.IsPointLike() and self.Source.IsNumeric()):
            nodeGraph.Assign(self.Destination, self.Source)
        else:
            print("Unhandled assign %s->%s" %
                  (self.Source.dataType, self.Destination.dataType))


class Opcode_return(Opcode):
    def __init__(self, OSO, index):
        Opcode.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        pass


class Opcode_dot(Opcode_DSS):
    def __init__(self, OSO, index):
        Opcode_DSS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        node = nodeGraph.CreateNode('ShaderNodeVectorMath')
        node.SetProperty("operation", "DOT_PRODUCT")
        nodeGraph.AddLink(node, 0, self.Source1)
        nodeGraph.AddLink(node, 1, self.Source2)
        nodeGraph.SetVar(self.Destination, node, 1)


class Opcode_length(Opcode_DS):
    def __init__(self, OSO, index):
        Opcode_DS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        node = nodeGraph.CreateNode('ShaderNodeSeparateXYZ')
        nodeGraph.AddLink(node, 0, self.Source)

        nodex = nodeGraph.CreateNode('ShaderNodeMath')
        nodex.SetProperty("operation", "MULTIPLY")
        nodeGraph.AddNodeLink(nodex, 0, node, 0)
        nodeGraph.AddNodeLink(nodex, 1, node, 0)

        nodey = nodeGraph.CreateNode('ShaderNodeMath')
        nodey.SetProperty("operation", "MULTIPLY")
        nodeGraph.AddNodeLink(nodey, 0, node, 1)
        nodeGraph.AddNodeLink(nodey, 1, node, 1)

        nodez = nodeGraph.CreateNode('ShaderNodeMath')
        nodez.SetProperty("operation", "MULTIPLY")
        nodeGraph.AddNodeLink(nodez, 0, node, 2)
        nodeGraph.AddNodeLink(nodez, 1, node, 2)

        node_add_xy = nodeGraph.CreateNode('ShaderNodeMath')
        node_add_xy.SetProperty("operation", "ADD")
        nodeGraph.AddNodeLink(node_add_xy, 0, nodex, 0)
        nodeGraph.AddNodeLink(node_add_xy, 1, nodey, 0)

        node_add_xyz = nodeGraph.CreateNode('ShaderNodeMath')
        node_add_xyz.SetProperty("operation", "ADD")
        nodeGraph.AddNodeLink(node_add_xyz, 0, node_add_xy, 0)
        nodeGraph.AddNodeLink(node_add_xyz, 1, nodez, 0)

        node_pow = nodeGraph.CreateNode('ShaderNodeMath')
        node_pow.SetProperty("operation", "POWER")
        nodeGraph.AddNodeLink(node_pow, 0, node_add_xyz, 0)
        node_pow.SetProperty("inputs[1].default_value", "0.5")

        nodeGraph.SetVar(self.Destination, node_pow, 0)


class Opcode_sqrt(Opcode_DS):
    def __init__(self, OSO, index):
        Opcode_DS.__init__(self, OSO, index)

    def Generate(self, nodeGraph, inverse=False):
        if (self.Source.IsNumeric()):
            node_pow = nodeGraph.CreateNode('ShaderNodeMath')
            node_pow.SetProperty("operation", "POWER")
            nodeGraph.AddLink(node_pow, 0, self.Source)
            node_pow.SetProperty("inputs[1].default_value", "0.5")
            node_result = node_pow

            if (inverse):
                node_div = nodeGraph.CreateNode('ShaderNodeMath')
                node_div.SetProperty("operation", "DIVIDE")
                node_div.SetProperty("inputs[0].default_value", "1")
                nodeGraph.AddNodeLink(node_div, 1, node, 0)
                node_result = node_div

            nodeGraph.SetVar(self.Destination, node_result, 0)
        elif (self.Source.IsPointLike()):
            node = nodeGraph.CreateNode('ShaderNodeSeparateXYZ')
            nodeGraph.AddLink(node, 0, self.Source)
            nodeOut = nodeGraph.CreateNode('ShaderNodeCombineXYZ')

            for i in range(3):
                node_pow = nodeGraph.CreateNode("ShaderNodeMath")
                node_pow.SetProperty("operation", "POWER")
                node_pow.SetProperty("inputs[1].default_value", "0.5")
                nodeGraph.AddNodeLink(node_pow, 0, node, i)
                node_result = node_pow

                if (inverse):
                    node_div = nodeGraph.CreateNode("ShaderNodeMath")
                    node_div.SetProperty("operation", "DIVIDE")
                    node_div.SetProperty("inputs[0].default_value", "1")
                    nodeGraph.AddNodeLink(node_div, 1, node_pow, 0)
                    node_result = node_div

                nodeGraph.AddNodeLink(nodeOut, i, node_result, 0)

            nodeGraph.SetVar(self.Destination, nodeOut, 0)


class Opcode_inversesqrt(Opcode_sqrt):
    def Generate(self, nodeGraph):
        super().Generate(nodeGraph, inverse=True)


class Opcode_neg(Opcode_DS):
    def __init__(self, OSO, index):
        Opcode_DS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        node = nodeGraph.CreateNode('ShaderNodeMath')
        node.SetProperty("operation", "MULTIPLY")
        nodeGraph.AddLink(node, 0, self.Source)
        node.SetProperty("inputs[1].default_value", "-1")
        nodeGraph.SetVar(self.Destination, node, 0)


class Opcode_floor(Opcode_basicMath1):
    def __init__(self, OSO, index):
        Opcode_basicMath1.__init__(self, OSO, index, 'FLOOR')


class Opcode_ceil(Opcode_basicMath1):
    def __init__(self, OSO, index):
        Opcode_basicMath1.__init__(self, OSO, index, 'CEIL')


class Opcode_round(Opcode_basicMath1):
    def __init__(self, OSO, index):
        Opcode_basicMath1.__init__(self, OSO, index, 'ROUND')


class Opcode_trunc(Opcode_DS):
    def __init__(self, OSO, index):
        Opcode_DS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        if (self.Source.IsPointLike()):
            node_mod = nodeGraph.CreateNode('ShaderNodeVectorMath')
            node_mod.SetProperty("operation", "MODULO")
            nodeGraph.AddLink(node_mod, 0, self.Source)
            node_mod.SetProperty("inputs[1].default_value[0]", "1")
            node_mod.SetProperty("inputs[1].default_value[1]", "1")
            node_mod.SetProperty("inputs[1].default_value[2]", "1")

            node_sub = nodeGraph.CreateNode('ShaderNodeVectorMath')
            node_sub.SetProperty("operation", "SUBTRACT")
            nodeGraph.AddLink(node_sub, 0, self.Source)
            nodeGraph.AddNodeLink(node_sub, 1, node_mod, 0)
        else:
            node_mod = nodeGraph.CreateNode('ShaderNodeMath')
            node_mod.SetProperty("operation", "MODULO")
            nodeGraph.AddLink(node_mod, 0, self.Source)
            node_mod.SetProperty("inputs[1].default_value", "1")

            node_sub = nodeGraph.CreateNode('ShaderNodeMath')
            node_sub.SetProperty("operation", "SUBTRACT")
            nodeGraph.AddLink(node_sub, 0, self.Source)
            nodeGraph.AddNodeLink(node_sub, 1, node_mod, 0)

        nodeGraph.SetVar(self.Destination, node_sub, 0)


class Opcode_abs(Opcode_basicMath1):
    def __init__(self, OSO, index):
        Opcode_basicMath1.__init__(self, OSO, index, 'ABSOLUTE')


class Opcode_fabs(Opcode_abs):
    pass


class Opcode_exp(Opcode_DS):
    def __init__(self, OSO, index):
        Opcode_DS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        if (self.Source.IsPointLike()):
            # split the source vector
            nodesplit = nodeGraph.CreateNode('ShaderNodeSeparateXYZ')
            nodeGraph.AddLink(nodesplit, 0, self.Source)
            mergevec = nodeGraph.CreateNode('ShaderNodeCombineXYZ')

            # exp the individial components
            for i in range(3):
                nodex = nodeGraph.CreateNode('ShaderNodeMath')
                nodex.SetProperty("operation", "POWER")
                nodex.SetProperty("inputs[0].default_value", "2.718281828459")
                nodeGraph.AddNodeLink(nodex, 1, nodesplit, i)

                # merge back into a vector
                nodeGraph.AddNodeLink(mergevec, i, nodex, 0)

            nodeGraph.SetVar(self.Destination, mergevec, 0)
        else:
            node = nodeGraph.CreateNode('ShaderNodeMath')
            node.SetProperty("operation", "POWER")
            node.SetProperty("inputs[0].default_value", "2.718281828459")
            nodeGraph.AddLink(node, 1, self.Source)
            nodeGraph.SetVar(self.Destination, node, 0)


class Opcode_exp2(Opcode_DS):
    def __init__(self, OSO, index):
        Opcode_DS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        if (self.Source.IsPointLike()):
            # split the source vector
            nodesplit = nodeGraph.CreateNode('ShaderNodeSeparateXYZ')
            nodeGraph.AddLink(nodesplit, 0, self.Source)
            mergevec = nodeGraph.CreateNode('ShaderNodeCombineXYZ')

            # exp2 the individial components
            for i in range(3):
                node_pow = nodeGraph.CreateNode('ShaderNodeMath')
                node_pow.SetProperty("operation", "POWER")
                node_pow.SetProperty("inputs[0].default_value", "2")
                nodeGraph.AddNodeLink(node_pow, 1, nodesplit, i)

                # merge back into a vector
                nodeGraph.AddNodeLink(mergevec, i, node_pow, 0)

            nodeOut = mergevec
        else:
            node = nodeGraph.CreateNode('ShaderNodeMath')
            node.SetProperty("operation", "POWER")
            node.SetProperty("inputs[0].default_value", "2")
            nodeGraph.AddLink(node, 1, self.Source)

            nodeOut = node

        nodeGraph.SetVar(self.Destination, nodeOut, 0)


class Opcode_expm1(Opcode_DS):
    def __init__(self, OSO, index):
        Opcode_DS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        if (self.Source.IsPointLike()):
            # split the source vector
            nodesplit = nodeGraph.CreateNode('ShaderNodeSeparateXYZ')
            nodeGraph.AddLink(nodesplit, 0, self.Source)
            mergevec = nodeGraph.CreateNode('ShaderNodeCombineXYZ')

            # expm1 the individial components
            for i in range(3):
                node_pow = nodeGraph.CreateNode('ShaderNodeMath')
                node_pow.SetProperty("operation", "POWER")
                node_pow.SetProperty("inputs[0].default_value", "2.718281828459")
                nodeGraph.AddNodeLink(node_pow, 1, nodesplit, i)

                node_sub = nodeGraph.CreateNode('ShaderNodeMath')
                node_sub.SetProperty("operation", "SUBTRACT")
                nodeGraph.AddNodeLink(node_sub, 0, node_pow, 0)
                node_sub.SetProperty("inputs[1].default_value", "1")

                # merge back into a vector
                nodeGraph.AddNodeLink(mergevec, i, node_sub, 0)

            nodeOut = mergevec
        else:
            node_pow = nodeGraph.CreateNode('ShaderNodeMath')
            node_pow.SetProperty("operation", "POWER")
            node_pow.SetProperty("inputs[0].default_value", "2.718281828459")
            nodeGraph.AddLink(node_pow, 1, self.Source)

            node_sub = nodeGraph.CreateNode('ShaderNodeMath')
            node_sub.SetProperty("operation", "SUBTRACT")
            nodeGraph.AddNodeLink(node_sub, 0, node_pow, 0)
            node_sub.SetProperty("inputs[1].default_value", "1")

            nodeOut = node_sub

        nodeGraph.SetVar(self.Destination, nodeOut, 0)


class Opcode_log(Opcode_DS):
    def __init__(self, OSO, index):
        self.argc = len(OSO.Instructions[index].Parameters)
        Opcode_DS.__init__(self, OSO, index)

    def Generate(self, nodeGraph, logValue="2.718281828459"):
        src = self.Source
        log = logValue

        node_min = nodeGraph.CreateNode("ShaderNodeValue")
        node_min.SetProperty("outputs[0].default_value", "1e-37")

        if (self.Source.IsPointLike()):
            # split the source vector
            nodesplit = nodeGraph.CreateNode("ShaderNodeSeparateXYZ")
            nodeGraph.AddLink(nodesplit, 0, src)
            mergevec = nodeGraph.CreateNode("ShaderNodeCombineXYZ")

            # log the individial components
            for i in range(3):
                node_gt = nodeGraph.CreateNode("ShaderNodeMath")
                node_gt.SetProperty("operation", "GREATER_THAN")
                nodeGraph.AddNodeLink(node_gt, 0, nodesplit, i)
                nodeGraph.AddNodeLink(node_gt, 1, node_min, 0)

                node_mix = nodeGraph.CreateNode("ShaderNodeMixRGB")
                nodeGraph.AddNodeLink(node_mix, 0, node_gt, 0)
                nodeGraph.AddNodeLink(node_mix, 1, node_min, 0)
                nodeGraph.AddNodeLink(node_mix, 2, nodesplit, i)

                node_separate = nodeGraph.CreateNode("ShaderNodeSeparateXYZ")
                nodeGraph.AddNodeLink(node_separate, 0, node_mix, 0)

                node_log = nodeGraph.CreateNode("ShaderNodeMath")
                node_log.SetProperty("operation", "LOGARITHM")
                nodeGraph.AddNodeLink(node_log, 0, node_separate, 0)
                node_log.SetProperty("inputs[1].default_value", log)

                # merge back into a vector
                nodeGraph.AddNodeLink(mergevec, i, node_log, 0)

            node_result = mergevec
        else:
            node_gt = nodeGraph.CreateNode("ShaderNodeMath")
            node_gt.SetProperty("operation", "GREATER_THAN")
            nodeGraph.AddLink(node_gt, 0, src)
            nodeGraph.AddNodeLink(node_gt, 1, node_min, 0)

            node_mix = nodeGraph.CreateNode("ShaderNodeMixRGB")
            nodeGraph.AddNodeLink(node_mix, 0, node_gt, 0)
            nodeGraph.AddNodeLink(node_mix, 1, node_min, 0)
            nodeGraph.AddLink(node_mix, 2, src)

            node_separate = nodeGraph.CreateNode("ShaderNodeSeparateXYZ")
            nodeGraph.AddNodeLink(node_separate, 0, node_mix, 0)

            node_log = nodeGraph.CreateNode("ShaderNodeMath")
            node_log.SetProperty("operation", "LOGARITHM")
            nodeGraph.AddNodeLink(node_log, 0, node_separate, 0)
            node_log.SetProperty("inputs[1].default_value", log)

            node_result = node_log

        nodeGraph.SetVar(self.Destination, node_result, 0)


class Opcode_log2(Opcode_log):
    def Generate(self, nodeGraph):
        super().Generate(nodeGraph, logValue="2")


class Opcode_log10(Opcode_log):
    def Generate(self, nodeGraph):
        super().Generate(nodeGraph, logValue="10")


class Opcode_logb(Opcode_log):
    def Generate(self, nodeGraph):
        if (self.Source.IsPointLike()):
            # absolute
            node_abs = nodeGraph.CreateNode('ShaderNodeVectorMath')
            node_abs.SetProperty("operation", "ABSOLUTE")
            nodeGraph.AddLink(node_abs, 0, self.Source)

            # split the source vector
            nodesplit = nodeGraph.CreateNode('ShaderNodeSeparateXYZ')
            nodeGraph.AddNodeLink(nodesplit, 0, node_abs, 0)
            mergevec = nodeGraph.CreateNode('ShaderNodeCombineXYZ')

            # log the individial components
            for i in range(3):
                node = nodeGraph.CreateNode('ShaderNodeMath')
                node.SetProperty("operation", "LOGARITHM")
                nodeGraph.AddNodeLink(node, 0, nodesplit, i)
                node.SetProperty("inputs[1].default_value", "2")

                # merge back into a vector
                nodeGraph.AddNodeLink(mergevec, i, node, 0)

            node_floor = nodeGraph.CreateNode('ShaderNodeVectorMath')
            node_floor.SetProperty("operation", "FLOOR")
            nodeGraph.AddNodeLink(node_floor, 0, mergevec, 0)

            node_result = node_floor
        else:
            # absolute
            node_abs = nodeGraph.CreateNode('ShaderNodeMath')
            node_abs.SetProperty("operation", "ABSOLUTE")
            nodeGraph.AddLink(node_abs, 0, self.Source)

            node = nodeGraph.CreateNode('ShaderNodeMath')
            node.SetProperty("operation", "LOGARITHM")
            nodeGraph.AddNodeLink(node, 0, node_abs, 0)
            node.SetProperty("inputs[1].default_value", "2")

            node_floor = nodeGraph.CreateNode('ShaderNodeMath')
            node_floor.SetProperty("operation", "FLOOR")
            nodeGraph.AddNodeLink(node_floor, 0, node, 0)

            node_result = node_floor

        nodeGraph.SetVar(self.Destination, node_result, 0)


class Opcode_sign(Opcode_DS):
    def __init__(self, OSO, index):
        Opcode_DS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        if (self.Source.IsPointLike()):
            # split the source vector
            nodesplit = nodeGraph.CreateNode('ShaderNodeSeparateXYZ')
            nodeGraph.AddLink(nodesplit, 0, self.Source)
            mergevec = nodeGraph.CreateNode('ShaderNodeCombineXYZ')

            # sign the individial components
            for i in range(3):
                node_abs = nodeGraph.CreateNode('ShaderNodeMath')
                node_abs.SetProperty("operation", "ABSOLUTE")
                nodeGraph.AddNodeLink(node_abs, 0, nodesplit, i)

                node_div = nodeGraph.CreateNode('ShaderNodeMath')
                node_div.SetProperty("operation", "DIVIDE")
                nodeGraph.AddNodeLink(node_div, 0, node_abs, 0)
                nodeGraph.AddNodeLink(node_div, 1, nodesplit, i)

                # merge back into a vector
                nodeGraph.AddNodeLink(mergevec, i, node_div, 0)

            nodeGraph.SetVar(self.Destination, mergevec, 0)
        else:
            node = nodeGraph.CreateNode('ShaderNodeMath')
            node.SetProperty("operation", "ABSOLUTE")
            nodeGraph.AddLink(node, 0, self.Source)

            node2 = nodeGraph.CreateNode('ShaderNodeMath')
            node2.SetProperty("operation", "DIVIDE")
            nodeGraph.AddNodeLink(node2, 0, node, 0)
            nodeGraph.AddLink(node2, 1, self.Source)
            nodeGraph.SetVar(self.Destination, node2, 0)


class Opcode_sincos(Opcode_SDD):
    def __init__(self, OSO, index):
        Opcode_SDD.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        if (self.Source.IsPointLike()):
            # split the source vector
            nodesplit = nodeGraph.CreateNode('ShaderNodeSeparateXYZ')
            nodeGraph.AddLink(nodesplit, 0, self.Source)
            mergevec_sin = nodeGraph.CreateNode('ShaderNodeCombineXYZ')
            mergevec_cos = nodeGraph.CreateNode('ShaderNodeCombineXYZ')

            # sincos (only x)
            node_sin = nodeGraph.CreateNode('ShaderNodeMath')
            node_sin.SetProperty("operation", "SINE")
            nodeGraph.AddNodeLink(node_sin, 0, nodesplit, 0)

            node_cos = nodeGraph.CreateNode('ShaderNodeMath')
            node_cos.SetProperty("operation", "COSINE")
            nodeGraph.AddNodeLink(node_cos, 0, nodesplit, 0)

            for i in range(3):
                # merge back into a vector
                nodeGraph.AddNodeLink(mergevec_sin, i, node_sin, 0)
                nodeGraph.AddNodeLink(mergevec_cos, i, node_cos, 0)

            nodeGraph.SetVar(self.Destination1, mergevec_sin, 0)
            nodeGraph.SetVar(self.Destination2, mergevec_cos, 0)
        elif (self.Source.IsNumeric()):
            node = nodeGraph.CreateNode('ShaderNodeMath')
            node.SetProperty("operation", "SINE")
            nodeGraph.AddLink(node, 0, self.Source)
            nodeGraph.SetVar(self.Destination1, node, 0)

            node2 = nodeGraph.CreateNode('ShaderNodeMath')
            node2.SetProperty("operation", "COSINE")
            nodeGraph.AddLink(node2, 0, self.Source)
            nodeGraph.SetVar(self.Destination2, node2, 0)


class Opcode_distance(Opcode_DSS):
    def __init__(self, OSO, index):
        Opcode_DSS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        node = nodeGraph.CreateNode("ShaderNodeVectorMath")
        node.SetProperty("operation", "SUBTRACT")
        nodeGraph.AddLink(node, 0, self.Source1)
        nodeGraph.AddLink(node, 1, self.Source2)

        node2 = nodeGraph.CreateNode('ShaderNodeVectorMath')
        node2.SetProperty("operation", "DOT_PRODUCT")
        nodeGraph.AddNodeLink(node2, 0, node, 0)
        nodeGraph.AddNodeLink(node2, 1, node, 0)

        node3 = nodeGraph.CreateNode('ShaderNodeMath')
        node3.SetProperty("operation", "POWER")
        nodeGraph.AddNodeLink(node3, 0, node2, 1)
        node3.SetProperty("inputs[1].default_value", "0.5")
        nodeGraph.SetVar(self.Destination, node3, 0)


class Opcode_smoothstep(Opcode):
    def __init__(self, OSO, index):
        Opcode.__init__(self, OSO, index)
        self.Destination = OSO.GetVariable(self.Instuction.Parameters[0])
        self.Source1 = OSO.GetVariable(self.Instuction.Parameters[1])
        self.Source2 = OSO.GetVariable(self.Instuction.Parameters[2])
        self.Fac = OSO.GetVariable(self.Instuction.Parameters[3])

    def Destination(self):
        return self.Destination

    def Source1(self):
        return self.Source1

    def Source2(self):
        return self.Source2

    def Fac(self):
        return self.Fac

    def Generate(self, nodeGraph):
        # (fac - Source1)
        node = nodeGraph.CreateNode('ShaderNodeMath')
        node.SetProperty("operation", "SUBTRACT")
        nodeGraph.AddLink(node, 0, self.Fac)
        nodeGraph.AddLink(node, 1, self.Source1)

        # (source2 - source1)
        node2 = nodeGraph.CreateNode('ShaderNodeMath')
        node2.SetProperty("operation", "SUBTRACT")
        nodeGraph.AddLink(node2, 0, self.Source2)
        nodeGraph.AddLink(node2, 1, self.Source1)

        # clamp ((fac - Source1) / (source2 - source1))
        node3 = nodeGraph.CreateNode('ShaderNodeMath')
        node3.SetProperty("operation", "DIVIDE")
        node3.SetProperty("use_clamp", "1")
        nodeGraph.AddNodeLink(node3, 0, node, 0)
        nodeGraph.AddNodeLink(node3, 1, node2, 0)
        nodeGraph.SetVar(self.Destination, node3, 0)
        # TODO polynomal


class Opcode_cos(Opcode_basicMath1):
    def __init__(self, OSO, index):
        Opcode_basicMath1.__init__(self, OSO, index, 'COSINE')


class Opcode_acos(Opcode_basicMath1):
    def __init__(self, OSO, index):
        Opcode_basicMath1.__init__(self, OSO, index, 'ARCCOSINE')


class Opcode_asin(Opcode_basicMath1):
    def __init__(self, OSO, index):
        Opcode_basicMath1.__init__(self, OSO, index, 'ARCSINE')


class Opcode_atan(Opcode_basicMath1):
    def __init__(self, OSO, index):
        Opcode_basicMath1.__init__(self, OSO, index, 'ARCTANGENT')


class Opcode_sin(Opcode_basicMath1):
    def __init__(self, OSO, index):
        Opcode_basicMath1.__init__(self, OSO, index, 'SINE')


class Opcode_tan(Opcode_basicMath1):
    def __init__(self, OSO, index):
        Opcode_basicMath1.__init__(self, OSO, index, 'TANGENT')


class Opcode_min(Opcode_basicMath):
    def __init__(self, OSO, index):
        Opcode_basicMath.__init__(self, OSO, index, "MINIMUM")


class Opcode_max(Opcode_basicMath):
    def __init__(self, OSO, index):
        Opcode_basicMath.__init__(self, OSO, index, "MAXIMUM")


class Opcode_div(Opcode_basicMath):
    def __init__(self, OSO, index):
        Opcode_basicMath.__init__(self, OSO, index, "DIVIDE")


class Opcode_mul(Opcode_basicMath):
    def __init__(self, OSO, index):
        Opcode_basicMath.__init__(self, OSO, index, "MULTIPLY")


class Opcode_pow(Opcode_basicMath):
    def __init__(self, OSO, index):
        Opcode_basicMath.__init__(self, OSO, index, "POWER")


class Opcode_add(Opcode_basicMath):
    def __init__(self, OSO, index):
        Opcode_basicMath.__init__(self, OSO, index, "ADD")


if (bpy.app.version < (2, 80, 0)):
    # https://blenderartists.org/forum/showthread.php?420857-What-can-you-do-with-lyapuno-and-mandelbrot-procedural-nodes&p=3184448&viewfull=1#post3184448
    class Opcode_atan2(Opcode_DSS):
        def __init__(self, OSO, index):
            Opcode_DSS.__init__(self, OSO, index)

        def Generate(self, nodeGraph):
            node = nodeGraph.CreateNode('ShaderNodeCombineXYZ')
            nodeGraph.AddLink(node, 0, self.Source2)
            nodeGraph.AddLink(node, 1, self.Source1)
            grad = nodeGraph.CreateNode('ShaderNodeTexGradient')
            grad.SetProperty("gradient_type", "'RADIAL'")
            nodeGraph.AddNodeLink(grad, 0, node, 0)
            nodem1 = nodeGraph.CreateNode('ShaderNodeMath')
            nodem1.SetProperty("operation", "SUBTRACT")
            nodem1.SetProperty("inputs[1].default_value", "0.5")
            nodeGraph.AddNodeLink(nodem1, 0, grad, 1)
            nodem2 = nodeGraph.CreateNode('ShaderNodeMath')
            nodem2.SetProperty("operation", "MULTIPLY")
            nodem2.SetProperty("inputs[1].default_value", "6.2831854")
            nodeGraph.AddNodeLink(nodem2, 0, nodem1, 0)
            nodeGraph.SetVar(self.Destination, nodem2, 0)
else:
    class Opcode_atan2(Opcode_basicMath):
        def __init__(self, OSO, index):
            Opcode_basicMath.__init__(self, OSO, index, 'ARCTAN2')


class Opcode_xor(Opcode_DSS):
    def __init__(self, OSO, index):
        Opcode_DSS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        nodem1 = nodeGraph.CreateNode('ShaderNodeMath')
        nodeGraph.AddLink(nodem1, 0, self.Source2)
        nodeGraph.AddLink(nodem1, 1, self.Source1)
        nodem1.SetProperty("operation", "ADD")
        nodem2 = nodeGraph.CreateNode('ShaderNodeMath')
        nodem2.SetProperty("operation", "MODULO")
        nodem2.SetProperty("inputs[1].default_value", "2")
        nodeGraph.AddNodeLink(nodem2, 0, nodem1, 0)
        nodeGraph.SetVar(self.Destination, nodem2, 0)


class Opcode_sub(Opcode_basicMath):
    def __init__(self, OSO, index):
        Opcode_basicMath.__init__(self, OSO, index, "SUBTRACT")


class Opcode_fmod(Opcode_basicMath):
    def __init__(self, OSO, index):
        Opcode_basicMath.__init__(self, OSO, index, "MODULO")

# mod(a,b) = A-B*(floor(a/b))


class Opcode_mod(Opcode_DSS):
    def __init__(self, OSO, index):
        Opcode_DSS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        # a/b
        node_adivb = nodeGraph.CreateNode('ShaderNodeMath')
        nodeGraph.AddLink(node_adivb, 0, self.Source1)
        nodeGraph.AddLink(node_adivb, 1, self.Source2)
        node_adivb.SetProperty("operation", "DIVIDE")

        # ((a/b)-0.5)
        node_floor1 = nodeGraph.CreateNode('ShaderNodeMath')
        node_floor1.SetProperty("inputs[1].default_value", "0.5")
        node_floor1.SetProperty("operation", "SUBTRACT")
        nodeGraph.AddNodeLink(node_floor1, 0, node_adivb, 0)

        # round((a/b)-0.5) = floor(a/b)
        node_floor2 = nodeGraph.CreateNode('ShaderNodeMath')
        node_floor2.SetProperty("operation", "ROUND")
        node_floor2.SetProperty("inputs[1].default_value", "0.5")
        nodeGraph.AddNodeLink(node_floor2, 0, node_floor1, 0)

        # B * floor(a/b)
        node_mul = nodeGraph.CreateNode('ShaderNodeMath')
        node_mul.SetProperty("operation", "MULTIPLY")
        nodeGraph.AddLink(node_mul, 0, self.Source2)
        nodeGraph.AddNodeLink(node_mul, 1, node_floor2, 0)

        # A - B * floor(a/b)
        node_sub = nodeGraph.CreateNode('ShaderNodeMath')
        node_sub.SetProperty("operation", "SUBTRACT")
        nodeGraph.AddLink(node_sub, 0, self.Source1)
        nodeGraph.AddNodeLink(node_sub, 1, node_mul, 0)

        # set output
        nodeGraph.SetVar(self.Destination, node_sub, 0)


# erf approximation: https://en.wikipedia.org/wiki/Error_function#Approximation_with_elementary_functions
class Opcode_erf(Opcode_DS):
    def __init__(self, OSO, index):
        Opcode_DS.__init__(self, OSO, index)

    def Generate(self, nodeGraph, erfc=False):
        src = self.Source

        # abs(x)
        node_abs = nodeGraph.CreateNode('ShaderNodeMath')
        node_abs.SetProperty("operation", "ABSOLUTE")
        nodeGraph.AddLink(node_abs, 0, src)

        # sign(x) = x / abs(x)
        node_sign = nodeGraph.CreateNode('ShaderNodeMath')
        node_sign.SetProperty("operation", "DIVIDE")
        nodeGraph.AddLink(node_sign, 0, src)
        nodeGraph.AddNodeLink(node_sign, 1, node_abs, 0)

        # e^(-(x^2)) = e^(-(x * x))
        node_e1 = nodeGraph.CreateNode('ShaderNodeMath')
        node_e1.SetProperty("operation", "MULTIPLY")
        nodeGraph.AddLink(node_e1, 0, src)
        nodeGraph.AddLink(node_e1, 1, src)

        node_e2 = nodeGraph.CreateNode('ShaderNodeMath')
        node_e2.SetProperty("operation", "MULTIPLY")
        nodeGraph.AddNodeLink(node_e2, 0, node_e1, 0)
        node_e2.SetProperty("inputs[1].default_value", "-1")

        node_e = nodeGraph.CreateNode('ShaderNodeMath')
        node_e.SetProperty("operation", "POWER")
        node_e.SetProperty("inputs[0].default_value", "2.718281828459")
        nodeGraph.AddNodeLink(node_e, 1, node_e2, 0)

        # t = 1 / (1 + p * abs(x))
        node_t1 = nodeGraph.CreateNode('ShaderNodeMath')
        node_t1.SetProperty("operation", "MULTIPLY")
        node_t1.SetProperty("inputs[0].default_value", "0.47047")
        nodeGraph.AddNodeLink(node_t1, 1, node_abs, 0)

        node_t2 = nodeGraph.CreateNode('ShaderNodeMath')
        node_t2.SetProperty("operation", "ADD")
        node_t2.SetProperty("inputs[0].default_value", "1")
        nodeGraph.AddNodeLink(node_t2, 1, node_t1, 0)

        node_t = nodeGraph.CreateNode('ShaderNodeMath')
        node_t.SetProperty("operation", "DIVIDE")
        node_t.SetProperty("inputs[0].default_value", "1")
        nodeGraph.AddNodeLink(node_t, 1, node_t2, 0)

        # erf(x) = 1 - (a1 * t + a2 * t^2 + a3 * t^3) * e^(-(x^2))
        #        = 1 - (t * (a1 + t * (a2 + t * a3))) * e^(-(x^2))
        # a1 = 0.3480242, a2 = −0.0958798, a3 = 0.7478556
        node_erf1 = nodeGraph.CreateNode('ShaderNodeMath')
        node_erf1.SetProperty("operation", "MULTIPLY")
        node_erf1.SetProperty("inputs[0].default_value", "0.7478556")
        nodeGraph.AddNodeLink(node_erf1, 1, node_t, 0)

        node_erf2 = nodeGraph.CreateNode('ShaderNodeMath')
        node_erf2.SetProperty("operation", "ADD")
        node_erf2.SetProperty("inputs[0].default_value", "-0.0958798")
        nodeGraph.AddNodeLink(node_erf2, 1, node_erf1, 0)

        node_erf3 = nodeGraph.CreateNode('ShaderNodeMath')
        node_erf3.SetProperty("operation", "MULTIPLY")
        nodeGraph.AddNodeLink(node_erf3, 0, node_erf2, 0)
        nodeGraph.AddNodeLink(node_erf3, 1, node_t, 0)

        node_erf4 = nodeGraph.CreateNode('ShaderNodeMath')
        node_erf4.SetProperty("operation", "ADD")
        node_erf4.SetProperty("inputs[0].default_value", "0.3480242")
        nodeGraph.AddNodeLink(node_erf4, 1, node_erf3, 0)

        node_erf5 = nodeGraph.CreateNode('ShaderNodeMath')
        node_erf5.SetProperty("operation", "MULTIPLY")
        nodeGraph.AddNodeLink(node_erf5, 0, node_erf4, 0)
        nodeGraph.AddNodeLink(node_erf5, 1, node_t, 0)

        node_erf6 = nodeGraph.CreateNode('ShaderNodeMath')
        node_erf6.SetProperty("operation", "MULTIPLY")
        nodeGraph.AddNodeLink(node_erf6, 0, node_erf5, 0)
        nodeGraph.AddNodeLink(node_erf6, 1, node_e, 0)

        node_erf7 = nodeGraph.CreateNode('ShaderNodeMath')
        node_erf7.SetProperty("operation", "SUBTRACT")
        node_erf7.SetProperty("inputs[0].default_value", "1")
        nodeGraph.AddNodeLink(node_erf7, 1, node_erf6, 0)

        # sign
        node_erf = nodeGraph.CreateNode('ShaderNodeMath')
        node_erf.SetProperty("operation", "MULTIPLY")
        nodeGraph.AddNodeLink(node_erf, 0, node_erf7, 0)
        nodeGraph.AddNodeLink(node_erf, 1, node_sign, 0)

        node_result = None
        if (erfc):
            node_erfc = nodeGraph.CreateNode('ShaderNodeMath')
            node_erfc.SetProperty("operation", "SUBTRACT")
            node_erfc.SetProperty("inputs[0].default_value", "1")
            nodeGraph.AddNodeLink(node_erfc, 1, node_erf, 0)
            node_result = node_erfc
        else:
            node_result = node_erf

        # set output
        nodeGraph.SetVar(self.Destination, node_result, 0)


class Opcode_erfc(Opcode_erf):
    def Generate(self, nodeGraph):
        super().Generate(nodeGraph, erfc=True)


# cosh(x) = (e^x + e^(-x)) / 2
class Opcode_cosh(Opcode_DS):
    def __init__(self, OSO, index):
        Opcode_DS.__init__(self, OSO, index)

    def Generate(self, nodeGraph, sinh=False):
        if (self.Source.IsPointLike()):
            nodesplit = nodeGraph.CreateNode('ShaderNodeSeparateXYZ')
            nodeGraph.AddLink(nodesplit, 0, self.Source)
            node_result = nodeGraph.CreateNode('ShaderNodeCombineXYZ')

            for i in range(3):
                # e^x
                node_ex1 = nodeGraph.CreateNode('ShaderNodeMath')
                node_ex1.SetProperty("operation", "POWER")
                node_ex1.SetProperty(
                    "inputs[0].default_value", "2.718281828459")
                nodeGraph.AddNodeLink(node_ex1, 1, nodesplit, i)

                # e^(-x)
                node_ex2 = nodeGraph.CreateNode('ShaderNodeMath')
                node_ex2.SetProperty("operation", "MULTIPLY")
                node_ex2.SetProperty("inputs[0].default_value", "-1")
                nodeGraph.AddNodeLink(node_ex2, 1, nodesplit, i)

                node_ex3 = nodeGraph.CreateNode('ShaderNodeMath')
                node_ex3.SetProperty("operation", "POWER")
                node_ex3.SetProperty(
                    "inputs[0].default_value", "2.718281828459")
                nodeGraph.AddNodeLink(node_ex3, 1, node_ex2, 0)

                # cosh: e^x + e^(-x) / 2
                # sinh: e^x - e^(-x) / 2
                node_ex4 = nodeGraph.CreateNode('ShaderNodeMath')
                node_ex4.SetProperty(
                    "operation", ("SUBTRACT" if sinh else "ADD"))
                nodeGraph.AddNodeLink(node_ex4, 0, node_ex1, 0)
                nodeGraph.AddNodeLink(node_ex4, 1, node_ex3, 0)

                node_cosh = nodeGraph.CreateNode('ShaderNodeMath')
                node_cosh.SetProperty("operation", "DIVIDE")
                nodeGraph.AddNodeLink(node_cosh, 0, node_ex4, 0)
                node_cosh.SetProperty("inputs[1].default_value", "2")

                nodeGraph.AddNodeLink(node_result, i, node_cosh, 0)
        else:
            # e^x
            node_ex1 = nodeGraph.CreateNode('ShaderNodeMath')
            node_ex1.SetProperty("operation", "POWER")
            node_ex1.SetProperty("inputs[0].default_value", "2.718281828459")
            nodeGraph.AddLink(node_ex1, 1, self.Source)

            # e^(-x)
            node_ex2 = nodeGraph.CreateNode('ShaderNodeMath')
            node_ex2.SetProperty("operation", "MULTIPLY")
            node_ex2.SetProperty("inputs[0].default_value", "-1")
            nodeGraph.AddLink(node_ex2, 1, self.Source)

            node_ex3 = nodeGraph.CreateNode('ShaderNodeMath')
            node_ex3.SetProperty("operation", "POWER")
            node_ex3.SetProperty("inputs[0].default_value", "2.718281828459")
            nodeGraph.AddNodeLink(node_ex3, 1, node_ex2, 0)

            # cosh: e^x + e^(-x) / 2
            # sinh: e^x - e^(-x) / 2
            node_ex4 = nodeGraph.CreateNode('ShaderNodeMath')
            node_ex4.SetProperty("operation", ("SUBTRACT" if sinh else "ADD"))
            nodeGraph.AddNodeLink(node_ex4, 0, node_ex1, 0)
            nodeGraph.AddNodeLink(node_ex4, 1, node_ex3, 0)

            node_result = nodeGraph.CreateNode('ShaderNodeMath')
            node_result.SetProperty("operation", "DIVIDE")
            nodeGraph.AddNodeLink(node_result, 0, node_ex4, 0)
            node_result.SetProperty("inputs[1].default_value", "2")

        # set output
        nodeGraph.SetVar(self.Destination, node_result, 0)


class Opcode_sinh(Opcode_cosh):
    def Generate(self, nodeGraph):
        super().Generate(nodeGraph, sinh=True)


# tanh(x) = sinh(x) / cosh(x)
class Opcode_tanh(Opcode_DS):
    def __init__(self, OSO, index):
        Opcode_DS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        if (self.Source.IsPointLike()):
            nodesplit = nodeGraph.CreateNode('ShaderNodeSeparateXYZ')
            nodeGraph.AddLink(nodesplit, 0, self.Source)
            node_result = nodeGraph.CreateNode('ShaderNodeCombineXYZ')

            for i in range(3):
                # e^x
                node_ex1 = nodeGraph.CreateNode('ShaderNodeMath')
                node_ex1.SetProperty("operation", "POWER")
                node_ex1.SetProperty(
                    "inputs[0].default_value", "2.718281828459")
                nodeGraph.AddNodeLink(node_ex1, 1, nodesplit, i)

                # e^(-x)
                node_ex2 = nodeGraph.CreateNode('ShaderNodeMath')
                node_ex2.SetProperty("operation", "MULTIPLY")
                node_ex2.SetProperty("inputs[0].default_value", "-1")
                nodeGraph.AddNodeLink(node_ex2, 1, nodesplit, i)

                node_ex3 = nodeGraph.CreateNode('ShaderNodeMath')
                node_ex3.SetProperty("operation", "POWER")
                node_ex3.SetProperty(
                    "inputs[0].default_value", "2.718281828459")
                nodeGraph.AddNodeLink(node_ex3, 1, node_ex2, 0)

                # sinh: e^x - e^(-x)
                node_sinh = nodeGraph.CreateNode('ShaderNodeMath')
                node_sinh.SetProperty("operation", "SUBTRACT")
                nodeGraph.AddNodeLink(node_sinh, 0, node_ex1, 0)
                nodeGraph.AddNodeLink(node_sinh, 1, node_ex3, 0)

                # cosh: e^x + e^(-x)
                node_cosh = nodeGraph.CreateNode('ShaderNodeMath')
                node_cosh.SetProperty("operation", "ADD")
                nodeGraph.AddNodeLink(node_cosh, 0, node_ex1, 0)
                nodeGraph.AddNodeLink(node_cosh, 1, node_ex3, 0)

                # tanh
                node_tanh = nodeGraph.CreateNode('ShaderNodeMath')
                node_tanh.SetProperty("operation", "DIVIDE")
                nodeGraph.AddNodeLink(node_tanh, 0, node_sinh, 0)
                nodeGraph.AddNodeLink(node_tanh, 1, node_cosh, 0)

                nodeGraph.AddNodeLink(node_result, i, node_tanh, 0)
        else:
            # e^x
            node_ex1 = nodeGraph.CreateNode('ShaderNodeMath')
            node_ex1.SetProperty("operation", "POWER")
            node_ex1.SetProperty("inputs[0].default_value", "2.718281828459")
            nodeGraph.AddLink(node_ex1, 1, self.Source)

            # e^(-x)
            node_ex2 = nodeGraph.CreateNode('ShaderNodeMath')
            node_ex2.SetProperty("operation", "MULTIPLY")
            node_ex2.SetProperty("inputs[0].default_value", "-1")
            nodeGraph.AddLink(node_ex2, 1, self.Source)

            node_ex3 = nodeGraph.CreateNode('ShaderNodeMath')
            node_ex3.SetProperty("operation", "POWER")
            node_ex3.SetProperty("inputs[0].default_value", "2.718281828459")
            nodeGraph.AddNodeLink(node_ex3, 1, node_ex2, 0)

            # sinh: e^x - e^(-x)
            node_sinh = nodeGraph.CreateNode('ShaderNodeMath')
            node_sinh.SetProperty("operation", "SUBTRACT")
            nodeGraph.AddNodeLink(node_sinh, 0, node_ex1, 0)
            nodeGraph.AddNodeLink(node_sinh, 1, node_ex3, 0)

            # cosh: e^x + e^(-x)
            node_cosh = nodeGraph.CreateNode('ShaderNodeMath')
            node_cosh.SetProperty("operation", "ADD")
            nodeGraph.AddNodeLink(node_cosh, 0, node_ex1, 0)
            nodeGraph.AddNodeLink(node_cosh, 1, node_ex3, 0)

            # tanh
            node_tanh = nodeGraph.CreateNode('ShaderNodeMath')
            node_tanh.SetProperty("operation", "DIVIDE")
            nodeGraph.AddNodeLink(node_tanh, 0, node_sinh, 0)
            nodeGraph.AddNodeLink(node_tanh, 1, node_cosh, 0)

            node_result = node_tanh

        # set output
        nodeGraph.SetVar(self.Destination, node_result, 0)


class Opcode_lt(Opcode_basicMath):
    def __init__(self, OSO, index):
        Opcode_basicMath.__init__(self, OSO, index, "LESS_THAN")

# todo le != lt, equal bit is missing...


class Opcode_le(Opcode_basicMath):
    def __init__(self, OSO, index):
        Opcode_basicMath.__init__(self, OSO, index, "LESS_THAN")


class Opcode_gt(Opcode_basicMath):
    def __init__(self, OSO, index):
        Opcode_basicMath.__init__(self, OSO, index, "GREATER_THAN")


class Opcode_ge(Opcode_DSS):
    def __init__(self, OSO, index):
        Opcode_DSS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        node = nodeGraph.CreateNode('ShaderNodeMath')
        node.SetProperty("operation", "SUBTRACT")
        nodeGraph.AddLink(node, 0, self.Source1)
        nodeGraph.AddLink(node, 1, self.Source2)

        node2 = nodeGraph.CreateNode('ShaderNodeMath')
        node2.SetProperty("operation", "ABSOLUTE")
        nodeGraph.AddNodeLink(node2, 0, node, 0)

        node3 = nodeGraph.CreateNode('ShaderNodeMath')
        node3.SetProperty("operation", "LESS_THAN")
        nodeGraph.AddNodeLink(node3, 0, node2, 0)
        node3.SetProperty("inputs[1].default_value", "0.000001")
        nodeGraph.SetVar(self.Destination, node3, 0)

        # Greater
        node4 = nodeGraph.CreateNode('ShaderNodeMath')
        node4.SetProperty("operation", "GREATER_THAN")
        nodeGraph.AddLink(node4, 0, self.Source1)
        nodeGraph.AddLink(node4, 1, self.Source2)

        # Greater + equal
        node5 = nodeGraph.CreateNode('ShaderNodeMath')
        node5.SetProperty("operation", "ADD")
        nodeGraph.AddNodeLink(node5, 0, node3, 0)
        nodeGraph.AddNodeLink(node5, 1, node4, 0)

        # //Greater + equal > 1
        node6 = nodeGraph.CreateNode("ShaderNodeMath")
        node6.SetProperty("operation", "GREATER_THAN")
        node6.SetProperty("inputs[1].default_value", "0.999")
        nodeGraph.AddNodeLink(node6, 0, node5, 0)

        nodeGraph.SetVar(self.Destination, node6, 0)


class Opcode_eq(Opcode_DSS):
    def __init__(self, OSO, index):
        Opcode_DSS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        node = nodeGraph.CreateNode('ShaderNodeMath')
        node.SetProperty("operation", "SUBTRACT")
        nodeGraph.AddLink(node, 0, self.Source1)
        nodeGraph.AddLink(node, 1, self.Source2)

        node2 = nodeGraph.CreateNode('ShaderNodeMath')
        node2.SetProperty("operation", "ABSOLUTE")
        nodeGraph.AddNodeLink(node2, 0, node, 0)

        node3 = nodeGraph.CreateNode('ShaderNodeMath')
        node3.SetProperty("operation", "LESS_THAN")
        nodeGraph.AddNodeLink(node3, 0, node2, 0)
        node3.SetProperty("inputs[1].default_value", "0.000001")
        nodeGraph.SetVar(self.Destination, node3, 0)


class Opcode_aassign(Opcode_DSS):
    def __init__(self, OSO, index):
        Opcode_DSS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        if not self.Source1.IsConst():
            print("only const array access is supported")
        if not self.Destination.IsArray():
            print("Target not an array")
        destvar = self.Destination.Name + "_" + self.Source1.defaults[0]
        nodeGraph.AAssign(destvar, self.Source2)


class Opcode_aref(Opcode_DSS):
    def __init__(self, OSO, index):
        Opcode_DSS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        if not self.Source2.IsConst():
            print("only const array access is supported")
        if not self.Source1.IsArray():
            print("Target not an array")
        sourcevar = self.Source1.Name + "_" + self.Source2.defaults[0]
        nodeGraph.ARef(self.Destination, sourcevar)


class Opcode_neq(Opcode_DSS):
    def __init__(self, OSO, index):
        Opcode_DSS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        node = nodeGraph.CreateNode('ShaderNodeMath')
        node.SetProperty("operation", "SUBTRACT")
        nodeGraph.AddLink(node, 0, self.Source1)
        nodeGraph.AddLink(node, 1, self.Source2)

        node2 = nodeGraph.CreateNode('ShaderNodeMath')
        node2.SetProperty("operation", "ABSOLUTE")
        nodeGraph.AddNodeLink(node2, 0, node, 0)

        node3 = nodeGraph.CreateNode('ShaderNodeMath')
        node3.SetProperty("operation", "GREATER_THAN")
        nodeGraph.AddNodeLink(node3, 0, node2, 0)
        node3.SetProperty("inputs[1].default_value", "0.00001")
        nodeGraph.SetVar(self.Destination, node3, 0)


class Opcode_point(Opcode_DSSS):
    def __init__(self, OSO, index):
        Opcode_DSSS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        node = nodeGraph.CreateNode('ShaderNodeCombineXYZ')
        nodeGraph.AddLink(node, 0, self.Source1)
        nodeGraph.AddLink(node, 1, self.Source2)
        nodeGraph.AddLink(node, 2, self.Source3)
        nodeGraph.SetVar(self.Destination, node, 0)


class Opcode_vector(Opcode_DSSS):
    def __init__(self, OSO, index):
        Opcode_DSSS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        node = nodeGraph.CreateNode('ShaderNodeCombineXYZ')
        nodeGraph.AddLink(node, 0, self.Source1)
        nodeGraph.AddLink(node, 1, self.Source2)
        nodeGraph.AddLink(node, 2, self.Source3)
        nodeGraph.SetVar(self.Destination, node, 0)


class Opcode_color(Opcode_vector):
    def __init__(self, OSO, index):
        Opcode_vector.__init__(self, OSO, index)


class Opcode_mix(Opcode_DSSS):
    def __init__(self, OSO, index):
        Opcode_DSSS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        if not self.Source3.IsFloat():
            print("mix only possible with float alpha")
        node = nodeGraph.CreateNode("ShaderNodeMixRGB")
        nodeGraph.AddLink(node, 0, self.Source3)
        nodeGraph.AddLink(node, 1, self.Source1)
        nodeGraph.AddLink(node, 2, self.Source2)
        nodeGraph.SetVar(self.Destination, node, 0)


class Opcode_normalize(Opcode_DS):
    def __init__(self, OSO, index):
        Opcode_DS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        node = nodeGraph.CreateNode("ShaderNodeVectorMath")
        node.SetProperty("operation", "NORMALIZE")
        nodeGraph.AddLink(node, 0, self.Source)
        nodeGraph.SetVar(self.Destination, node, 0)


class Opcode_backfacing(Opcode_D):
    def __init__(self, OSO, index):
        Opcode_D.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        node = nodeGraph.CreateNode("ShaderNodeGeometry")
        nodeGraph.SetVar(self.Destination, node, 6)


class Opcode_isconnected(Opcode_DS):
    def __init__(self, OSO, index):
        Opcode_DS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        node = nodeGraph.CreateNode('ShaderNodeValue')
        node.SetProperty('outputs[0].default_value', 1)
        nodeGraph.SetVar(self.Destination, node, 0)


class Opcode_cross(Opcode_DSS):
    def __init__(self, OSO, index):
        Opcode_DSS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        node = nodeGraph.CreateNode("ShaderNodeVectorMath")
        node.SetProperty("operation", "CROSS_PRODUCT")
        nodeGraph.AddLink(node, 0, self.Source1)
        nodeGraph.AddLink(node, 1, self.Source2)
        nodeGraph.SetVar(self.Destination, node, 0)


class Opcode_step(Opcode_DSS):
    def __init__(self, OSO, index):
        Opcode_DSS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        node = nodeGraph.CreateNode("ShaderNodeMath")
        node.SetProperty("operation", "LESS_THAN")
        nodeGraph.AddLink(node, 0, self.Source1)
        nodeGraph.AddLink(node, 1, self.Source2)

        nodeGraph.SetVar(self.Destination, node, 0)


class Opcode_noise(Opcode):
    def __init__(self, OSO, index):
        Opcode.__init__(self, OSO, index)
        self.Destination = OSO.GetVariable(self.Instuction.Parameters[0])
        if (len(self.Instuction.Parameters) == 3):
            self.Source1 = OSO.GetVariable(self.Instuction.Parameters[1])
            self.Source2 = OSO.GetVariable(self.Instuction.Parameters[2])
        elif (len(self.Instuction.Parameters) == 2):
            self.Source1 = OSOVariable('const	string	uperlin	"uperlin"')
            self.Source2 = OSO.GetVariable(self.Instuction.Parameters[1])
        if (len(self.Instuction.Parameters) == 4): #TODO: period is ignored. 
            self.Source1 = OSO.GetVariable(self.Instuction.Parameters[1])
            self.Source2 = OSO.GetVariable(self.Instuction.Parameters[2])

    def Destination(self):
        return self.Destination

    def Source1(self):
        return self.Source1

    def Source2(self):
        return self.Source2

    def Generate(self, nodeGraph):

            if self.Source1.defaults[0] in ['"uperlin"','"noise"'] :
                node = nodeGraph.CreateNode("ShaderNodeTexNoise")
                node.SetProperty("inputs[1].default_value", "1.0")
                node.SetProperty("inputs[2].default_value", "0.0")
                node.SetProperty("inputs[3].default_value", "0.0")
                nodeGraph.AddLink(node, 0, self.Source2)
                if (self.Destination.IsFloat()):
                    nodeGraph.SetVar(self.Destination, node, 1)
                elif (self.Destination.IsPointLike()):
                    nodeGraph.SetVar(self.Destination, node, 0)

            if self.Source1.defaults[0] in ['"perlin"','"snoise"',"perlin","snoise"] :
                node = nodeGraph.CreateNode("ShaderNodeTexNoise")
                node.SetProperty("inputs[1].default_value", "1.0")
                node.SetProperty("inputs[2].default_value", "0.0")
                node.SetProperty("inputs[3].default_value", "0.0")
                nodeGraph.AddLink(node, 0, self.Source2)

                if (self.Destination.IsFloat()):
                    # ShaderNodeTexNoise outputs 0..1 , perlin output -1..1 , adjust by val = (val - 0.5)*2
                    node2 = nodeGraph.CreateNode("ShaderNodeMath")
                    node2.SetProperty("operation", "SUBTRACT")
                    node2.SetProperty("inputs[1].default_value", "0.5")
                    nodeGraph.AddNodeLink(node2, 0, node, 0)

                    node3 = nodeGraph.CreateNode("ShaderNodeMath")
                    node3.SetProperty("operation", "MULTIPLY")
                    node3.SetProperty("inputs[1].default_value", "2")
                    nodeGraph.AddNodeLink(node3, 0, node2, 0)
                    nodeGraph.SetVar(self.Destination, node3, 0)
                elif (self.Destination.IsPointLike()):
                     # split the source vector
                    nodesplit = nodeGraph.CreateNode('ShaderNodeSeparateXYZ')
                    nodeGraph.AddNodeLink(nodesplit, 0, node, 0)

                    # floor the individial components
                    nodex = nodeGraph.CreateNode('ShaderNodeMath')
                    nodex.SetProperty("operation", "SUBTRACT")
                    nodeGraph.AddNodeLink(nodex, 0, nodesplit, 0)
                    nodex.SetProperty("inputs[1].default_value", "0.5")

                    nodex1 = nodeGraph.CreateNode('ShaderNodeMath')
                    nodex1.SetProperty("operation", "MULTIPLY")
                    nodex1.SetProperty("inputs[1].default_value", "2")
                    nodeGraph.AddNodeLink(nodex1, 0, nodex, 0)

                    nodey = nodeGraph.CreateNode('ShaderNodeMath')
                    nodey.SetProperty("operation", "SUBTRACT")
                    nodeGraph.AddNodeLink(nodey, 0, nodesplit, 1)
                    nodey.SetProperty("inputs[1].default_value", "0.5")

                    nodey1 = nodeGraph.CreateNode('ShaderNodeMath')
                    nodey1.SetProperty("operation", "MULTIPLY")
                    nodey1.SetProperty("inputs[1].default_value", "2")
                    nodeGraph.AddNodeLink(nodey1, 0, nodey, 0)
                
                    nodez = nodeGraph.CreateNode('ShaderNodeMath')
                    nodez.SetProperty("operation", "SUBTRACT")
                    nodeGraph.AddNodeLink(nodez, 0, nodesplit, 2)
                    nodez.SetProperty("inputs[1].default_value", "0.5")

                    nodez1 = nodeGraph.CreateNode('ShaderNodeMath')
                    nodez1.SetProperty("operation", "MULTIPLY")
                    nodez1.SetProperty("inputs[1].default_value", "2")
                    nodeGraph.AddNodeLink(nodez1, 0, nodez, 0)

                    # merge back into a vector
                    mergevec = nodeGraph.CreateNode('ShaderNodeCombineXYZ')
                    nodeGraph.AddNodeLink(mergevec, 0, nodex1, 0)
                    nodeGraph.AddNodeLink(mergevec, 1, nodey1, 0)
                    nodeGraph.AddNodeLink(mergevec, 2, nodez1, 0)

                    nodeGraph.SetVar(self.Destination, mergevec, 0)
                else:
                    print("unknown noise target")

            if self.Source1.defaults[0] in ['"cell"','cell'] :
                # split the source vector
                node = nodeGraph.CreateNode('ShaderNodeSeparateXYZ')
                nodeGraph.AddLink(node, 0, self.Source2)

                # floor the individial components
                nodex = nodeGraph.CreateNode('ShaderNodeMath')
                nodex.SetProperty("operation", "SUBTRACT")
                nodeGraph.AddNodeLink(nodex, 0, node, 0)
                nodex.SetProperty("inputs[1].default_value", "0.5")

                nodex1 = nodeGraph.CreateNode('ShaderNodeMath')
                nodex1.SetProperty("operation", "ROUND")
                nodeGraph.AddNodeLink(nodex1, 0, nodex, 0)

                nodey = nodeGraph.CreateNode('ShaderNodeMath')
                nodey.SetProperty("operation", "SUBTRACT")
                nodeGraph.AddNodeLink(nodey, 0, node, 1)
                nodey.SetProperty("inputs[1].default_value", "0.5")

                nodey1 = nodeGraph.CreateNode('ShaderNodeMath')
                nodey1.SetProperty("operation", "ROUND")
                nodeGraph.AddNodeLink(nodey1, 0, nodey, 0)
                
                nodez = nodeGraph.CreateNode('ShaderNodeMath')
                nodez.SetProperty("operation", "SUBTRACT")
                nodeGraph.AddNodeLink(nodez, 0, node, 2)
                nodez.SetProperty("inputs[1].default_value", "0.5")

                nodez1 = nodeGraph.CreateNode('ShaderNodeMath')
                nodez1.SetProperty("operation", "ROUND")
                nodeGraph.AddNodeLink(nodez1, 0, nodez, 0)

                # merge back into a vector
                floorvec = nodeGraph.CreateNode('ShaderNodeCombineXYZ')
                nodeGraph.AddNodeLink(floorvec, 0, nodex1, 0)
                nodeGraph.AddNodeLink(floorvec, 1, nodey1, 0)
                nodeGraph.AddNodeLink(floorvec, 2, nodez1, 0)

                # get some cell noise
                vor = nodeGraph.CreateNode('ShaderNodeTexVoronoi')
                vor.SetProperty("coloring", "'CELLS'")
                nodeGraph.AddNodeLink(vor, 0, floorvec, 0)
                # if the destination is a vector, just assign it
                if (self.Destination.IsPointLike()):
                    nodeGraph.SetVar(self.Destination, vor, 0)
                else: # if it is a number, split the color and pick the first channel, the fact output of the texture averages the rgb channels and ruins the nice flat 0..1 distribution
                    nodeSplit = nodeGraph.CreateNode('ShaderNodeSeparateXYZ')
                    nodeGraph.AddNodeLink(nodeSplit, 0, vor, 0)
                    nodeGraph.SetVar(self.Destination, nodeSplit, 0)
            else:
                print("unsupporte noise type %s" % self.Source1.defaults[0])


class Opcode_compassign(Opcode_DIS):
    def __init__(self, OSO, index):
        Opcode_DIS.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        if '$const' not in self.Index.Name:
            print("compref only possible with const index")
        if not self.Destination.IsPointLike():
            print("compref only possible on point like types")
        idx = int(self.Index.defaults[0])
        nodeIn = nodeGraph.CreateNode("ShaderNodeSeparateXYZ")
        nodeGraph.AddLink(nodeIn, 0, self.Destination)
        nodeOut = nodeGraph.CreateNode('ShaderNodeCombineXYZ')
        if idx != 0:
            nodeGraph.AddNodeLink(nodeOut, 0, nodeIn, 0)
        if idx != 1:
            nodeGraph.AddNodeLink(nodeOut, 1, nodeIn, 1)
        if idx != 2:
            nodeGraph.AddNodeLink(nodeOut, 2, nodeIn, 2)
        nodeGraph.AddLink(nodeOut, idx, self.Source)
        nodeGraph.SetVar(self.Destination, nodeOut, 0)


class Opcode_compref(Opcode_DSI):
    def __init__(self, OSO, index):
        Opcode_DSI.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        if '$const' not in self.Index.Name:
            print("compref only possible with const index")
        if not self.Source.IsPointLike():
            print("compref only possible on point like types")
        idx = int(self.Index.defaults[0])
        node = nodeGraph.CreateNode("ShaderNodeSeparateXYZ")
        nodeGraph.SetVar(self.Destination, node, idx)
        nodeGraph.AddLink(node, 0, self.Source)


class Opcode_end(Opcode):
    def __init__(self, OSO, index):
        Opcode.__init__(self, OSO, index)

    def Generate(self, nodeGraph):
        pass


class Opcode_functioncall(Opcode):
    def __init__(self, OSO, index):
        Opcode.__init__(self, OSO, index)
        self.Instructions = []
        self.FunctionEnd = int(self.Instuction.Parameters[1])
        idx = index + 1
        while (idx < self.FunctionEnd):
            instance = OSO.MakeOpcode(idx)
            self.Instructions.append(instance)
            idx = instance.NextIndex()

    def NextIndex(self):
        return self.FunctionEnd

    def Generate(self, nodeGraph):
        for inst in self.Instructions:
            inst.Generate(nodeGraph)


class Opcode_if_vars:
    def __init__(self):
        self.InitialValue = {}
        self.TrueValue = {}
        self.FalseValue = {}


class basicLoop(Opcode):
    def __init__(self, OSO, index):
        Opcode.__init__(self, OSO, index)
        self.Condition = OSO.GetVariable(self.Instuction.Parameters[0])
        self.InitLabel = int(self.Instuction.Parameters[1])
        self.IterLabel = int(self.Instuction.Parameters[2])
        self.BodyLabel = int(self.Instuction.Parameters[3])
        self.DoneLabel = int(self.Instuction.Parameters[4])
        self.InitCode = []
        self.IterCode = []
        self.BodyCode = []
        self.DoneCode = []
        idx = index + 1
        while (idx <= self.InitLabel):
            instance = OSO.MakeOpcode(idx)
            self.InitCode.append(instance)
            idx = instance.NextIndex()
        while (idx <= self.IterLabel):
            instance = OSO.MakeOpcode(idx)
            self.IterCode.append(instance)
            idx = instance.NextIndex()
        while (idx <= self.BodyLabel):
            instance = OSO.MakeOpcode(idx)
            self.BodyCode.append(instance)
            idx = instance.NextIndex()
        while (idx <= self.DoneLabel):
            instance = OSO.MakeOpcode(idx)
            self.DoneCode.append(instance)
            idx = instance.NextIndex()
        self.Next = idx

    def NextIndex(self):
        return self.Next

    def Generate(self, nodeGraph):
        # sanity checks.

        # We take the lowerbound + looping var from the InitCode
        if len(self.InitCode) != 1:
            raise ValueError("cannot determine loop bounds")

        # must be an assign opcode
        if self.InitCode[0].Instuction.Opcode != "assign":
            raise ValueError("cannot determine loop bounds")

        if len(self.IterCode) != 1:
            raise ValueError("cannot determine loop bounds")

        # must be an lt opcode
        if self.IterCode[0].Instuction.Opcode != "lt":
            raise ValueError("cannot determine loop bounds")

        loopVar = self.InitCode[0].Instuction.Parameters[0]
        LowerBound = self.InitCode[0].Instuction.Parameters[1]
        UpperBound = self.IterCode[0].Instuction.Parameters[2]

        # make sure the lower and upper bounds are consts
        if not self.OSO.GetVariable(LowerBound).IsConst():
            raise ValueError("cannot determine loop bounds")

        if not self.OSO.GetVariable(UpperBound).IsConst():
            raise ValueError("cannot determine loop bounds")

        AddVar = None
        # Locate the incrementer in the done code and be sure it's const
        for inst in self.DoneCode:
            if (inst.Instuction.Opcode == 'add' and
                    inst.Instuction.Parameters[0] == loopVar):
                AddVar = inst.Instuction.Parameters[2]
                break

        if not AddVar:
            raise ValueError("cannot determine loop bounds")

        if not self.OSO.GetVariable(AddVar).IsConst():
            raise ValueError("cannot determine loop bounds")

        for inst in self.InitCode:
            inst.Generate(nodeGraph)

        lowerBoundFloat = float(self.OSO.GetVariable(LowerBound).defaults[0])
        upperBoundFloat = float(self.OSO.GetVariable(UpperBound).defaults[0])
        adderFloat = float(self.OSO.GetVariable(AddVar).defaults[0])
        for value in float_range(lowerBoundFloat,
                                 upperBoundFloat,
                                 adderFloat):
            print("Loop iteration %s" % value)
            for inst in self.IterCode:
                inst.Generate(nodeGraph)
            for inst in self.BodyCode:
                inst.Generate(nodeGraph)
            for inst in self.DoneCode:
                inst.Generate(nodeGraph)


class Opcode_for(basicLoop):
    def __init__(self, OSO, index):
        basicLoop.__init__(self, OSO, index)


class Opcode_if(Opcode):
    def __init__(self, OSO, index):
        Opcode.__init__(self, OSO, index)
        self.Condition = OSO.GetVariable(self.Instuction.Parameters[0])
        self.TrueLabel = int(self.Instuction.Parameters[1])
        self.FalseLabel = int(self.Instuction.Parameters[2])
        self.TrueCode = []
        self.FalseCode = []
        idx = index + 1
        while (idx <= self.TrueLabel):
            instance = OSO.MakeOpcode(idx)
            self.TrueCode.append(instance)
            idx = instance.NextIndex()
        while (idx <= self.FalseLabel):
            instance = OSO.MakeOpcode(idx)
            self.FalseCode.append(instance)
            idx = instance.NextIndex()
        self.Next = idx

    def NextIndex(self):
        return self.Next

    def Resolve(self, nodeGraph, name, ConditionVar, TrueValue, FalseValue):
        node = nodeGraph.CreateNode("ShaderNodeMixRGB")
        nodeGraph.AddLink(node, 0, ConditionVar)
        nodeGraph.AddNodeLink(node, 1, FalseValue.Node, FalseValue.Output)
        nodeGraph.AddNodeLink(node, 2, TrueValue.Node, TrueValue.Output)
        nodeGraph.SetVar(name, node, 0)

    def Generate(self, nodeGraph):
        print("Building IF")
        InitialState = nodeGraph.Variables.copy()
        for inst in self.TrueCode:
            print("Generating index %s opcode %s" % ( inst.InstructionIndex, inst.Instuction))
            inst.Generate(nodeGraph)
        TrueState = nodeGraph.Variables.copy()
        nodeGraph.Variables = InitialState.copy()
        for inst in self.FalseCode:
            print("Generating index %s opcode %s" % ( inst.InstructionIndex, inst.Instuction))
            inst.Generate(nodeGraph)
        FalseState = nodeGraph.Variables.copy()
        nodeGraph.Variables = InitialState.copy()
        print("Resolving variables")
        Values = {}
        for var in InitialState:
            if var not in Values.keys():
                Values[var] = Opcode_if_vars()
            Values[var].InitialValue = InitialState[var]
        for var in TrueState:
            if var not in Values.keys():
                Values[var] = Opcode_if_vars()
            Values[var].TrueValue = TrueState[var]
        for var in FalseState:
            if var not in Values.keys():
                Values[var] = Opcode_if_vars()
            Values[var].FalseValue = FalseState[var]

        # remove all vars that have not been changed
        for var in Values.copy().keys():
            ConditionTrueAndFalseEqual = (
                Values[var].FalseValue == Values[var].TrueValue and
                Values[var].TrueValue == Values[var].InitialValue
            )
            if ConditionTrueAndFalseEqual:
                del Values[var]

        for var in Values.keys():
            ConditionTrueAndFalseDifferent = (
                Values[var].TrueValue and
                Values[var].FalseValue and
                Values[var].TrueValue != Values[var].FalseValue)
            if ConditionTrueAndFalseDifferent:
                self.Resolve(nodeGraph,
                             self.OSO.GetVariable(var),
                             self.Condition,
                             Values[var].TrueValue,
                             Values[var].FalseValue)
            else:
                if Values[var].TrueValue and Values[var].InitialValue:
                    self.Resolve(nodeGraph,
                                 self.OSO.GetVariable(var),
                                 self.Condition,
                                 Values[var].TrueValue,
                                 Values[var].InitialValue)
                else:
                    if Values[var].FalseValue and Values[var].InitialValue:
                        self.Resolve(nodeGraph,
                                     self.OSO.GetVariable(var),
                                     self.Condition,
                                     Values[var].InitialValue,
                                     Values[var].FalseValue)
                    else:
                       if Values[var].FalseValue:
                         nodeGraph.SetVar(self.OSO.GetVariable(var), Values[var].FalseValue.Node, Values[var].FalseValue.Output)
                       else:
                         if Values[var].TrueValue:
                            nodeGraph.SetVar(self.OSO.GetVariable(var), Values[var].TrueValue.Node, Values[var].TrueValue.Output)
                            
                    # these are values that are just set in the true or false
                    # branch, and should not be referenced after this block
                    # is finished, safe to ignore
                    # else:
                    #    print("???")
