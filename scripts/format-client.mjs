import fs from 'node:fs'
import path from 'node:path'
import ts from '../frontend/node_modules/typescript/lib/typescript.js'

const root = path.resolve(import.meta.dirname, '../frontend/src')
function walk(folder) {
  return fs.readdirSync(folder, {withFileTypes:true}).flatMap(entry=>entry.isDirectory()?walk(path.join(folder,entry.name)):[path.join(folder,entry.name)])
}
for (const file of walk(root).filter(file=>/\.tsx?$/.test(file))) {
  let source = fs.readFileSync(file, 'utf8')
  if (!file.endsWith('main.tsx')) source=source.replace("import '@xyflow/react/dist/style.css'", '')
  const ast = ts.createSourceFile(file,source,ts.ScriptTarget.Latest,true,file.endsWith('.tsx')?ts.ScriptKind.TSX:ts.ScriptKind.TS)
  const changes=[]
  for (const statement of ast.statements) {
    if (!ts.isImportDeclaration(statement)||!statement.importClause) continue
    const clause=statement.importClause
    const keep=name=>(source.match(new RegExp('\\b'+name+'\\b','g'))||[]).length>1
    const defaultName=clause.name&&keep(clause.name.text)?clause.name:undefined
    let bindings=clause.namedBindings
    if (bindings&&ts.isNamedImports(bindings)) {
      const elements=bindings.elements.filter(spec=>keep(spec.name.text))
      bindings=elements.length?ts.factory.updateNamedImports(bindings,elements):undefined
    }
    if (!defaultName&&!bindings) changes.push([statement.getStart(ast),statement.end,''])
    else {
      const next=ts.factory.updateImportDeclaration(statement,statement.modifiers,ts.factory.updateImportClause(clause,clause.isTypeOnly,defaultName,bindings),statement.moduleSpecifier,statement.attributes)
      changes.push([statement.getStart(ast),statement.end,ts.createPrinter().printNode(ts.EmitHint.Unspecified,next,ast)])
    }
  }
  for(const [start,end,text] of changes.reverse()) source=source.slice(0,start)+text+source.slice(end)
  const result=ts.createSourceFile(file,source,ts.ScriptTarget.Latest,true,file.endsWith('.tsx')?ts.ScriptKind.TSX:ts.ScriptKind.TS)
  fs.writeFileSync(file,ts.createPrinter({newLine:ts.NewLineKind.LineFeed}).printFile(result))
}
