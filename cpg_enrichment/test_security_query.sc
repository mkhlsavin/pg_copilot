cpg.call.where(_.tag.nameExact("security-risk")).map(c => (c.name, c.filename, c.lineNumber)).l.take(5)
