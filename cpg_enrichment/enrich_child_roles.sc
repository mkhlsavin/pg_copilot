// enrich_child_roles.sc - annotate AST child nodes with semantic roles
// Launch: :load enrich_child_roles.sc
//
// Tags emitted:
//   - `child-role`
//   - `tag-confidence`
//
// ============================================================================

import io.shiftleft.codepropertygraph.generated.nodes._
import io.shiftleft.semanticcpg.language._
import flatgraph.{DiffGraphApplier, DiffGraphBuilder}
import java.util.Locale

import EnrichCommon._

val APPLY = sys.props.getOrElse("childroles.apply", "true").toBoolean

println(s"[*] Apply child role enrichment: $APPLY")

if (!APPLY) {
  println("[*] Child role enrichment skipped (set -Dchildroles.apply=true to run).")
} else {

  val diff = DiffGraphBuilder(cpg.graph.schema)
  var tagged = 0L

  def lr(value: String): String = value.toLowerCase(Locale.ROOT)

  def codeOf(node: AstNode): String =
    Option(node.code).map(_.toString).getOrElse("")

  def isComment(node: AstNode): Boolean = node.label == "COMMENT"

  def addRole(node: AstNode, role: String, confidence: String = "medium"): Unit = {
    if (role.nonEmpty && Tagging.addTag(node, TagCatalog.ChildRole.name, lr(role), diff)) {
      Tagging.addConfidence(node, confidence, diff)
      tagged += 1
    }
  }

  def handleIf(cs: ControlStructure): Unit = {
    cs.astChildren.l.foreach { child =>
      val ord = child.order
      if (ord >= 0 && !isComment(child)) {
        ord match {
          case 1 =>
            addRole(child, "condition", "high")
          case _ =>
            child match {
              case block: Block =>
                addRole(block, "then-body")
              case nested: ControlStructure if Option(nested.controlStructureType).exists(_.equalsIgnoreCase("ELSE")) =>
                addRole(nested, "else-branch")
                nested.astChildren.l.foreach { elseChild =>
                  if (!isComment(elseChild)) {
                    elseChild match {
                      case elseBlock: Block => addRole(elseBlock, "else-body")
                      case other            => addRole(other, "else-body")
                    }
                  }
                }
              case other =>
                addRole(other, "then-body")
            }
        }
      }
    }
  }

  def handleElse(cs: ControlStructure): Unit = {
    cs.astChildren.l.foreach {
      case block: Block if !isComment(block) => addRole(block, "else-body")
      case child if !isComment(child)        => addRole(child, "else-body")
      case _                                 => // ignore comments
    }
  }

  def handleFor(cs: ControlStructure): Unit = {
    cs.astChildren.l.foreach { child =>
      if (!isComment(child)) {
        child.order match {
          case 1 =>
            if (child.label == "LOCAL" || codeOf(child).contains("=")) addRole(child, "loop-initializer")
          case 2 =>
            if (child.label == "CALL") addRole(child, "loop-initializer")
          case 3 =>
            if (child.label == "CALL") addRole(child, "loop-condition", "high")
          case 4 =>
            if (child.label == "CALL") addRole(child, "loop-update")
            else if (child.label == "BLOCK") addRole(child, "loop-body")
          case ord if ord >= 5 && child.label == "BLOCK" =>
            addRole(child, "loop-body")
          case _ if child.label == "BLOCK" =>
            addRole(child, "loop-body")
          case _ =>
            ()
        }
      }
    }
  }

  def handleWhile(cs: ControlStructure): Unit = {
    cs.astChildren.l.foreach { child =>
      if (!isComment(child)) {
        child.order match {
          case 1 => addRole(child, "loop-condition", "high")
          case _ if child.label == "BLOCK" => addRole(child, "loop-body")
          case _ => ()
        }
      }
    }
  }

  def handleDo(cs: ControlStructure): Unit = {
    cs.astChildren.l.foreach { child =>
      if (!isComment(child)) {
        child.order match {
          case 1 if child.label == "BLOCK" => addRole(child, "loop-body")
          case _                           => addRole(child, "loop-condition")
        }
      }
    }
  }

  def handleSwitch(cs: ControlStructure): Unit = {
    cs.astChildren.l.foreach { child =>
      if (!isComment(child)) {
        child.order match {
          case 1 => addRole(child, "switch-selector", "high")
          case _ if child.label == "BLOCK" => addRole(child, "switch-body")
          case _ => ()
        }
      }
    }
  }

  def handleCase(cs: ControlStructure, role: String): Unit = {
    cs.astChildren.l.foreach { child =>
      if (!isComment(child)) {
        if (child.label == "BLOCK") addRole(child, role) else addRole(child, role)
      }
    }
  }

  def handleGeneric(cs: ControlStructure): Unit = {
    cs.astChildren.l.foreach { child =>
      if (!isComment(child)) {
        child.order match {
          case 1 if child.label == "CALL" || child.label == "IDENTIFIER" => addRole(child, "condition")
          case _ if child.label == "BLOCK" => addRole(child, "control-body")
          case _ => ()
        }
      }
    }
  }

  cpg.controlStructure.l.foreach { cs =>
    Option(cs.controlStructureType).map(_.toUpperCase(Locale.ROOT)) match {
      case Some("IF")    => handleIf(cs)
      case Some("ELSE")  => handleElse(cs)
      case Some("FOR")   => handleFor(cs)
      case Some("WHILE") => handleWhile(cs)
      case Some("DO")    => handleDo(cs)
      case Some("SWITCH") => handleSwitch(cs)
      case Some("CASE")   => handleCase(cs, "case-body")
      case Some("DEFAULT") => handleCase(cs, "case-body")
      case _ => handleGeneric(cs)
    }
  }

  cpg.ret.l.foreach { ret =>
    ret.astChildren.l.foreach { child =>
      if (child.order >= 0 && !isComment(child)) {
        addRole(child, "return-value", "medium")
      }
    }
  }

  println("[*] Applying child role enrichment diff...")
  DiffGraphApplier.applyDiff(cpg.graph, diff)
  println(f"[+] Child role enrichment complete. Tagged $tagged%,d nodes.")
}
