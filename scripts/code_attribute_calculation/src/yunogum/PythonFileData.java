package yunogum;

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.github.gumtreediff.actions.Diff;
import com.github.gumtreediff.actions.TreeClassifier;
import com.github.gumtreediff.actions.model.Action;
import com.github.gumtreediff.actions.model.Insert;
import com.github.gumtreediff.actions.model.TreeInsert;
import com.github.gumtreediff.tree.Tree;

public class PythonFileData {
    //the range of characters around we take when determining metrics 
    public static final int metricsCharacterRange = 512;
    public static boolean IGNORE_RANGE = false;;
    public int commentedLineNo;       
    public int extendedRangestartLine;       
    public int extendedRangeEndLine;       
    
    public int extendedNodeRangeStart;
    public int extendedNodeRangeEnd;

    public int extendedCharRangeStart;
    public int extendedCharRangeEnd;
    
    public int lineOuterNodeStart;
    public int lineOuterNodeEnd;

    public int lineCharStart;
    public int lineCharEnd;

    public Tree containerFunction;
    

    public List<Tree> treesInExtendedRangeOfLine;
    public List<Tree> treesInRangeOfLine;
    public List<Integer> srcCharCountUptoLine;
    public List<Integer> dstCharCountUptoLine;
    String filePath;
    public Map<Tree, InsertAction> dstTreeToSrcInsertActionMap;
    public Diff diff;
    public TreeClassifier classifier;
    private int extendedRangeStartLineNo;
    private int extendedRangeEndLineNo;
    
    /**
     * Get list of trees spanning range. Does not contain subtrees of a tree that is within range. Only the
     * @param results
     * @param root
     * @param startPos
     * @param endPos
     */
    public static void fetchTreesSpanningRange(List<Tree> results,Tree root, int startPos, int endPos){
        //if node is in range add to list and stop
        if(root.getPos() >= startPos && root.getEndPos() <= endPos){
            results.add(root);
            return;
        }
        boolean containsRange = root.getPos() <= startPos && root.getEndPos() >= endPos;
        boolean containsStartOfRange = root.getPos() <= startPos && startPos < root.getEndPos();
        boolean containesEndOfRange = root.getPos() <= endPos && endPos < root.getEndPos();
        // System.out.println(root);
        // System.out.println("containsRange " + containsRange);
        // System.out.println("containsStartOfRange " + containsStartOfRange);
        // System.out.println("containesEndOfRange " + containesEndOfRange);
        //if node overlaps range try to add children
        if(containsRange || containsStartOfRange || containesEndOfRange ){
            for (Tree child : root.getChildren()) {
                fetchTreesSpanningRange(results, child, startPos, endPos);
            }
        }
        //if node overlaps edge of range add if no other in overlapping edge is in list(they would be in start and end) positions already
        if(containsStartOfRange){
            //#TODO check if this was supposed to be >=
            if(results.size() <= 0 || results.get(0).getPos() > startPos){
                results.add(0, root);
            }else if(results.get(0).getPos() < root.getPos() ){
                results.set(0, root);
            }
        }

        if(containesEndOfRange){
            //#TODO check if this was supposed to be <=
            if(results.size() <= 0 || results.get(results.size() -1).getEndPos() < endPos){
                results.add(root);
            }else if (results.get(results.size() -1).getEndPos() > root.getEndPos()){
                results.set(results.size() -1 , root);
            }
        }
    }


    void printFile(){

        try(BufferedReader br = new BufferedReader(new FileReader(filePath)))
        {
            String line = null; 

            int l = 1;
            while ((line = br.readLine()) != null)  
            {  
                
                System.out.println("LineNo: " + l + " : "+ line + " | "  + getLineStartCharPos(l, srcCharCountUptoLine) + " to " + getLineEndCharPos(l, srcCharCountUptoLine) );
                l++;
            }
            
        }catch(Exception e){

        }
    }

    public boolean checkIfInFunctionScope(Tree t){
        if(!MetricRunner.USE_FUNCTION_SCOPE)
            return true;
        
        return containerFunction == null || (containerFunction.getPos() <= t.getPos() && containerFunction.getEndPos() <= t.getEndPos());
    }

    /**
     * Get the character index the line ends on
     * @param lineNo
     * @param charCountUpToLine
     * @return
     */
    static int getLineEndCharPos(int lineNo, List<Integer> charCountUpToLine){
        //we inserted extra char for len of last list
            
        if(charCountUpToLine.size() <= 0){
            return 0;
        }
        if(lineNo >= charCountUpToLine.size()){
            return charCountUpToLine.get(charCountUpToLine.size() -1);
        }
        // you can subtract one to not count the \n
        // int endCharPos = (charCountUpToLine.get(lineNo) )-1;
        int endCharPos = charCountUpToLine.get(lineNo) ;
        return endCharPos;
    }

    static int getLineStartCharPos(int lineNo, List<Integer> charCountUpToLine){
        if(charCountUpToLine.size() <= 0 || lineNo <= 0){
            return 0;
        }
        if(lineNo >= charCountUpToLine.size()){
            return charCountUpToLine.get(charCountUpToLine.size() -1);
        }
        int charCount = charCountUpToLine.get(lineNo - 1);

        return charCount > 0? charCount : 0;
    }
    // static Tree getSmallestTreeContainingRange(Tree root, int startPos, int endPos){
    //     Tree result = null;

    //     // if(root.getPos() >= startPos && root.getEndPos() <= endPos){
    //     //     result = root;
    //     // }
    //     //else 
    //     if(root.getPos() <= startPos   && root.getEndPos() >= endPos)
    //     //we always start from tree root so if selection is inside code then the  comdition will be fufilled
    //     //but the commented line could be in a code comment comment before the code starts
    //     //in which case, the subject of the comment is code comment 
    //     //we can still get a tree if the the root fell within range
    //     //or atleast part of ot 
    //     //and null will be returned
    //     {
    //         while(true){

    //             if(result.isLeaf())
    //                 break;
    
    //             Tree chosenChild = null;
    //             for (Tree child : result.getChildren()) {
    //                 if(child.getPos() >= startPos && child.getEndPos() <= endPos){
    //                     chosenChild = child;
    //                     break;
    //                 }
    //             }

    //             if(chosenChild == null)
    //                 break;
    //             result = chosenChild;
    //         }
    //     }
        

    //     return result;
    // }

    // static Tree getSmallestTreeContainingLine(Tree root, int lineStart, List<Integer> charCountUpToLine){

    //     //get entire file if last line else get lien size by subtracting from next line
    //     return getSmallestTreeContainingRange(root, charCountUpToLine.get(lineStart -1), getLineEndCharPos(lineStart, charCountUpToLine));
    // }

    /**
     * Get whether the line is within start and end pos of given root
     * @param root
     * @param charCountAtLine
     * @return
     */
    public static boolean isLineOutOfTreeRange(Tree root, int charCountAtLine){
        return charCountAtLine < root.getPos() || charCountAtLine > root.getEndPos();
    }
    public static PythonFileData parseFile(String srcFile,String dstFile,int lineNo, Diff diff, TreeClassifier classifier){
        if(lineNo<= 0){
            System.out.println("#################################");
            System.out.println("#DO NOT USE ZERO INDEX FOR LINE.#");
            System.out.println("#################################");
        }
        List<Integer> srcCharCountUptoLine = countCharsUpToEachLine(srcFile, lineNo);
        List<Integer> dstCharCountUptoLine = countCharsUpToEachLine(dstFile, lineNo);
        int totalLineCount = srcCharCountUptoLine.size() > 0? (srcCharCountUptoLine.size() -1 ) : 0; 
        // for (Integer integer : charCountUptoLine) {
        //     if(l == charCountUptoLine.size())
        //         break;
        //     int lineEndPos =  getLineEndCharPos(l, charCountUptoLine);
        //     MetricRunner.dlog("lineno " +l +" : "  + integer + "," + lineEndPos);
        //     l++;
        // }

        int offset = metricsCharacterRange/2;

        //this can still get tree parts that are part of an expressions
        // ex x = a+ b+ c...rest and we get + c...rest which is nonsensical
        // for now ignore that
        // MetricRunner.dlog("tree:\n"+tc);
        Tree root = diff.src.getRoot();

        // MetricRunner.dlog("root pos " + root.getPos());

        int lineStartPos = getLineStartCharPos(lineNo, srcCharCountUptoLine);
        int lineEndPos = getLineEndCharPos(lineNo, srcCharCountUptoLine);
        
        //character count based offset
        // int rangeStartPos = lineStartPos - offset;
        // int rangeEndPos = lineStartPos + offset-1;

        //+- lines based offset
        int startLine = lineNo - MetricRunner.LINE_RANGE; 
        if(lineNo <= MetricRunner.LINE_RANGE){
            startLine = 0;
        }
        int endLine = startLine + MetricRunner.LINE_RANGE * 2;
        if(endLine >= totalLineCount){ 
            endLine = totalLineCount;
        }

        int rangeStartPos = getLineStartCharPos(startLine, srcCharCountUptoLine);
        int rangeEndPos = getLineEndCharPos(endLine, srcCharCountUptoLine);


        // MetricRunner.dlog((lineNo - 1) +" : ranged children from " + lineStartPos +" ["+ rangeStartPos + "," + rangeEndPos);
        
        //get the smalllest node containing range with offset
        // Tree t = getSmallestTreeContainingRange(root, startPos-offset, startPos+offset);
        List<Tree> rangeTrees = new ArrayList<>();
        fetchTreesSpanningRange(rangeTrees, root, rangeStartPos,rangeEndPos );
        if(MetricRunner.DEBUG){
            MetricRunner.dlog("get the smalllest node containing range with offset::::::::::::::::::::::::");
            for (Tree tree : rangeTrees) {
                MetricRunner.dlog(tree.toTreeString());
            }
        }
        
        List<Tree> lineTrees = new ArrayList<>();
        fetchTreesSpanningRange(lineTrees, root, lineStartPos, lineEndPos);
        if(MetricRunner.DEBUG){
            MetricRunner.dlog("trees around line::::::::::::::::::::::::");
            for (Tree tree : lineTrees) {
                MetricRunner.dlog(tree.toTreeString());
            }
        }

        Tree containerFunction = null;
        if(MetricRunner.USE_FUNCTION_SCOPE){
            if (lineTrees.size() > 0) {
                // System.out.println("use line tree : " + lineTrees.get(0).toString());

                containerFunction = getParentFunction(lineTrees.get(0));

                // if function definitions are nested, on the line where the nested function
                // starts,
                // this detects the parent function
                // that is not necessarily a bad thing
                // as you can say that the parent function is the scope for any change involving
                // the line
                // and I will not fix it.
               
            } else {
                // System.out.println("use range tree");
                // it is possible that the line range mismatches and there is no one node that
                // fully inside line
                // the expanded range will probably have the node
                // the expanded range could have part of other functions
                // so we check for the node that contains/overlaps the linerange
                // if it does overlap, there might be another but the parent for all of them
                // will be same
                // so we can immediately look for function from that parent
                Tree workingParent = null;
                for (Tree t : rangeTrees) {
                    if (t.getPos() >= rangeStartPos && t.getEndPos() <= rangeStartPos) {
                        workingParent = t;
                        break;
                    }
                    if (t.getPos() <= rangeStartPos && t.getEndPos() >= rangeStartPos) {
                        workingParent = t;
                        break;
                    }

                }
                if (workingParent != null) {
                    containerFunction = getParentFunction(containerFunction);
                }

            }
        }

        PythonFileData fileData = new PythonFileData(srcFile, lineNo,
            startLine, endLine,
            rangeStartPos, rangeEndPos,
            lineStartPos, lineEndPos, diff, classifier, containerFunction,
            rangeTrees, lineTrees, srcCharCountUptoLine);

        return fileData;
    }

    public static Tree getParentFunction(Tree child){
        //node we start at could be function itself
        Tree cur = child;
        while(cur != null){
            if(AstUtils.isTreeType(cur, AstUtils.funcdef)){
                return cur;
            }
            cur = cur.getParent();
        }
        return null;
    }

    static List<Integer> countCharsUpToEachLine(String filePath,int lineNo){
        
        List<Integer> results = new ArrayList<>();

        try(BufferedReader br = new BufferedReader(new FileReader(filePath)))
        {
            String line = null; 

            int runningCount = 0;
            results.add(runningCount);
            int l = 0;
            while ((line = br.readLine()) != null)  
            {  
                //we are  reading lines, not the entire file char by char
                //this means that we ignore the additional \n character
                //this'll break if newlien is two characters 
                //but it's not for the files I've looked at.
                
                //let's pray that's the case because otherwise we'll need to go thrugh the file char by char and detect newline manually
                runningCount +=  line.length() + 1;
                l++;
                // if(++l == lineNo){
                    // System.out.println("LineNo: " + l + " : " + line+ " len add: " + (line.length() + 1) + " total " + runningCount);

                // }
                results.add(runningCount);//the last value is the count of cahrs in file
                //maybe need to compensate for 
            }
            
        }catch(Exception e){

        }
        return results;
    }


    PythonFileData(String filePath, int lineNo,
            int extendedRangestartLine, int extendedRangeEndLine,
            int extendedRangeStart, int extendedRangeEnd, 
            int lineCharStart, int lineCharEnd,
            Diff diff, TreeClassifier classifier,
            Tree containerFunction,
            List<Tree> treesInExtendedRangeOfLine, List<Tree> treesInRangeOfLine, List<Integer> charCountUptoLine) {
        this.filePath = filePath;
        this.commentedLineNo = lineNo;
        this.extendedRangestartLine = extendedRangestartLine;
        this.extendedRangeEndLine = extendedRangeEndLine;
        this.extendedCharRangeStart = extendedRangeStart;
        this.extendedCharRangeEnd = extendedRangeEnd;
        this.lineCharStart = lineCharStart;
        this.lineCharEnd = lineCharEnd;
        this.treesInExtendedRangeOfLine = treesInExtendedRangeOfLine;
        this.treesInRangeOfLine = treesInRangeOfLine;
        this.srcCharCountUptoLine = charCountUptoLine;
        this.containerFunction = containerFunction;

        this.extendedNodeRangeStart = treesInExtendedRangeOfLine.size() > 0
        ? treesInExtendedRangeOfLine.get(0).getPos() 
        : extendedRangeStart;

        this.extendedNodeRangeEnd = treesInExtendedRangeOfLine.size() > 0
        ? treesInExtendedRangeOfLine.get(treesInExtendedRangeOfLine.size() - 1).getEndPos() 
        : extendedRangeEnd;

        this.lineOuterNodeStart = treesInRangeOfLine.size() > 0
        ? treesInRangeOfLine.get(0).getPos() 
        : lineCharStart;

        this.lineOuterNodeEnd = treesInRangeOfLine.size() > 0
        ? treesInRangeOfLine.get(treesInRangeOfLine.size()-1).getEndPos() 
        : lineCharEnd;

        this.diff = diff;
        this.classifier = classifier;
        
        this.dstTreeToSrcInsertActionMap = mapDstTreeToSrcInsertionActions(diff);

        // extendedRangeStartLineNo = 1;
        // extendedRangeEndLineNo = charCountUptoLine.size();
        
        // for(int i = lineNo-1; i >= 1;i-- ){
        //     if(getLineStartCharPos(i, charCountUptoLine) <= (lineCharStart - (metricsCharacterRange/2))){
        //         extendedRangeStartLineNo = i;
        //         break;
        //     }
        // }

        // for(int i = lineNo+1; i < charCountUptoLine.size() && i >= 0;i++ ){
        //     if(getLineStartCharPos(i, charCountUptoLine) >= (lineCharStart + (metricsCharacterRange/2))){
        //         extendedRangeEndLineNo = i;
        //         break;
        //     }
        // }
    }

    /**
     * Find the character index where a child inserted at given index would start from
     * NOT ACCURATE when comments are present
     * @param parent
     * @param childIndex
     * @return
     */
    static int getChildInsertionPos(Tree parent,int childIndex){
        if(parent.getChildren().size() <= 0){
            return parent.getPos();//#TODO a parent without children shouldn't exist but if it does it could contain a comment at start making insertpos innacurate
        }

        //insert after last one
        if(childIndex >= parent.getChildren().size()  ){
            return parent.getChild(parent.getChildren().size() -1 ).getEndPos();
        }
        return parent.getChild(childIndex).getPos();// also will ignore tabs at start of line but that information is lost at AST level
    }

    int getImmediateChildIndexContainingTree(Tree parent, Tree tree){
        int childIndex = 0;
        for (Tree childTree : parent.getChildren()) {
            if(childTree.getPos() <= tree.getPos() && tree.getEndPos() <= childTree.getEndPos())
                return childIndex;
                childIndex++;
        }
        return -1;
    }


    Map<Tree, InsertAction> mapDstTreeToSrcInsertionActions(Diff diff){
        Map<Tree, InsertAction>  result = new HashMap<>();
        for (Action action : diff.editScript) {
            
            // MetricRunner.dlog("action : " +  action.getName());
            Tree dstTree = null;
            Tree givenParent = null;
            int givenPos  =-1;
            Tree srcParent = null;
            int childInsertionIndex = -1;
            //single node added ex: foo(a) => foo(a,b) b is a leaf not a tree
            if(action instanceof  Insert){
                { 
                    Insert insertion = (Insert) action;
                    if (insertion != null) {
                        dstTree = insertion.getNode();
                        givenParent = insertion.getParent();
                        givenPos = insertion.getPosition();
                    }
                }
            }
            //inserted an atcual tree instead a small node
            if(action instanceof  TreeInsert){
                TreeInsert treeInsertion = (TreeInsert) action;
                if (treeInsertion != null) {
                    dstTree = treeInsertion.getNode();
                    givenParent = treeInsertion.getParent();
                    givenPos = treeInsertion.getPosition();
                }
            }
            if(dstTree != null ){

                if(diff.mappings.getDstForSrc(givenParent) == null ){
                    // MetricRunner.dlog("insertion parent dest-> src not exist" + dstTree.toTreeString());
                    //the insertion parent should have a mapping to dst if it was a insertion parent in src
                    //since it doesn't, we assume that it's the case where the parent type changed between src and dst
                    //and this parent is  the parent of the ndoe in dst, based on example case results
                    Tree mappedDstParent = getDstNodeParentOverlappingExtendedRange(givenParent);
                    if(mappedDstParent == null)
                    {
                        // MetricRunner.dlog("insertion parent src->dst ALSO not exist");
                    }else{
                        srcParent = diff.mappings.getSrcForDst(mappedDstParent);
                        if(srcParent != null && isSrcNodeInExtendedRange(srcParent)){
                            int indexOfNextDstNodeInParentChain = getImmediateChildIndexContainingTree(mappedDstParent, dstTree);
                            childInsertionIndex = indexOfNextDstNodeInParentChain;
                        }
                    }
                }else{
                    srcParent = givenParent;
                    childInsertionIndex = givenPos;
                    // MetricRunner.dlog("normal insertion at " + childInsertionIndex +" of \n" + srcParent.toTreeString() +"\n <- \n" +  dstTree.toTreeString() );
                }
                if(srcParent != null && childInsertionIndex >= 0){
                    int insertionPos = getChildInsertionPos(srcParent, childInsertionIndex);
                    if(insertionPos >= extendedNodeRangeStart && insertionPos <= extendedNodeRangeEnd){
                        result.put(dstTree, new InsertAction(srcParent,dstTree, childInsertionIndex, insertionPos ));
                        // MetricRunner.dlog(
                        //     "insertion at child index " + childInsertionIndex + " out of " + srcParent.getChildren().size() + " at "
                        //     // +insertionPos 
                        //     +" : \n" +
                        //     dstTree.toTreeString());
                        // MetricRunner.dlog("parent mapped to src: \n" +srcParent.toTreeString());
                    }
                }
            }

        }


        // edit action seems to ignore children of inserted and only contain parent 
        // this means that if a large insertion block happend containing important inserted tree types as children,
        // they would get ignored
        // we need to add them
        // However, we only need to check the trees that are children to the trees already added
        // so we extract the current keyset to a list and check from there
        List<InsertAction> insertedContainer = new ArrayList<>();
        for (InsertAction tree : result.values()) {
            insertedContainer.add(tree);
        }
        for (Tree tree : classifier.getInsertedDsts()) {
            for (InsertAction containerInsertAction  : insertedContainer) {
                if(tree.getPos() >= containerInsertAction.dstTree.getPos() && tree.getEndPos() <= containerInsertAction.dstTree.getEndPos()){
                    result.put(tree, containerInsertAction);
                }
            }
        }
        return result;
    }
    
    public boolean isSrcNodeInExtendedRange(Tree node){
        if(IGNORE_RANGE)
            return true;
        return node.getPos() >= extendedNodeRangeStart && node.getEndPos() <= extendedNodeRangeEnd;
    }

    public boolean isSrcNodeFullyOutsideExtendedRange(Tree node){
        if(IGNORE_RANGE)
            return true;
        return node.getEndPos() <= extendedNodeRangeStart || node.getPos() >= extendedNodeRangeEnd;
    }
    
    public boolean isSrcNodeInLineRange(Tree node){
        if(IGNORE_RANGE)
            return true;
        return node.getPos() >= lineOuterNodeStart && node.getEndPos() <= lineOuterNodeEnd;
    }

    public  boolean isSrcNodeFullyOutsideLineRange(Tree node){
        if(IGNORE_RANGE)
            return true;
        return node.getEndPos() <= lineOuterNodeStart || node.getPos() >= lineOuterNodeEnd;
    }



    boolean isDstNodeInLineRange(Tree dstNode){
        if(IGNORE_RANGE)
            return true;
        Tree mappedSrcNode = diff.mappings.getSrcForDst(dstNode);
        if(mappedSrcNode != null){
            if(isSrcNodeInLineRange(mappedSrcNode)){
                return true;
            }else if(isSrcNodeFullyOutsideLineRange(mappedSrcNode)){
                return false;
            }else{//#TODO overlap edges of range edgecase. For now return false
                return false;
            }
        }else{
            if(dstNode.getParent() == null){
                return false;
            }else{
                return isDstNodeInLineRange(dstNode.getParent());
            }
        }
    }

    /**
     * Find first parent(that mapps to something in src tree) of a dst tree node. THIS RETURNS A DST TREE NODE 
     * @param dstNode
     * @param diff
     * @return SAID PARENT IN DST TREE, null if outside range or overlap but not contain range  
     */
    public Tree getDstNodeParentOverlappingLineRange(Tree dstNode,Diff diff){
        Tree mappedSrcNode = diff.mappings.getSrcForDst(dstNode);
        if(mappedSrcNode != null){
            if(isSrcNodeInLineRange(mappedSrcNode)){
                return dstNode;
            }else if(isSrcNodeFullyOutsideLineRange(mappedSrcNode)){
                return null;
            }else{//#TODO overlap edges of range edgecase. For now return false
                return null;
            }
        }else{
            if(dstNode.getParent() == null){
                return null;
            }else{
                return getDstNodeParentOverlappingLineRange(dstNode.getParent(), diff);
            }
        }
    }

        /**
     * Find  first parent(that mapps to something in src tree) of a dst tree node. THIS RETURNS A DST TREE NODE
     * @param dstNode
     * @param diff
     * @return SAID PARENT IN DST TREE, null if outside range or overlap but not contain range 
     */
    public Tree getDstNodeParentOverlappingExtendedRange(Tree dstNode){
        Tree mappedSrcNode = diff.mappings.getSrcForDst(dstNode);
        // MetricRunner.dlog("getparent overlap " + dstNode + " x " + mappedSrcNode); 
        if(mappedSrcNode != null){
            if(isSrcNodeInExtendedRange(mappedSrcNode)){
                return dstNode;
            }else if(isSrcNodeFullyOutsideExtendedRange(mappedSrcNode)){
                return null;
            }else{//#TODO overlap edges of range edgecase. For now return false
                return null;
            }
        }else{
            if(dstNode.getParent() == null){
                return null;
            }else{
                return getDstNodeParentOverlappingExtendedRange(dstNode.getParent());
            }
        }
    }

    public boolean isInsertedNodeInExtendedRange(Tree insertedDstNode){
        return isInsertedNodeInRange(insertedDstNode,extendedNodeRangeStart,extendedNodeRangeEnd);
    }

    public boolean isInsertedNodeInRange(Tree insertedDstNode, int rangeStart, int rangeEnd){
        if(IGNORE_RANGE)
            return true;
        InsertAction insertAction = dstTreeToSrcInsertActionMap.getOrDefault(insertedDstNode, null);
        
        if(insertAction == null){
            // MetricRunner.dlog("   insrtion action null for " + insertedDstNode.toTreeString());
            return false;
        }else{
            int insertionPositionInSrc = getChildInsertionPos(insertAction.mappedSrcParent, insertAction.insertionIndex);
            // MetricRunner.dlog("insertionPositionInSrc " + insertionPositionInSrc + " parent \n" + insertAction.mappedSrcParent.toTreeString() + "child no " + insertAction.insertionIndex );
            return insertionPositionInSrc >= rangeStart && insertionPositionInSrc <= rangeEnd;
        }
    }


    public boolean isDstNodeInExtendedRange(Tree dstNode){
        if(IGNORE_RANGE)
            return true;
        Tree mappedSrcNode = diff.mappings.getSrcForDst(dstNode);
        if(mappedSrcNode != null){
            if(isSrcNodeInExtendedRange(mappedSrcNode)){
                return true;
            }else if(isSrcNodeFullyOutsideExtendedRange(mappedSrcNode)){
                return false;
            }else{//#TODO overlap edges of range edgecase. For now return false
                return false;
            }
        }else{
            if(dstNode.getParent() == null){
                return false;
            }else{
                return isDstNodeInExtendedRange(dstNode.getParent());
            }
        }
    }

    String describeContainerFunction(){
        if(containerFunction == null){
            return "No parent Function";
        }else{
            int l = 0;
            for(int startPos : srcCharCountUptoLine){
                if(startPos >= containerFunction.getPos())
                    break;
                l++; 
            }
            return containerFunction + " " + containerFunction.getLabel() +" : " + "at line " + l + " from " +  containerFunction.getPos()+ " to " + containerFunction.getEndPos()   +"\n";
        }


    }
    @Override
    public String toString() {
 
    
        return "lineNo " + commentedLineNo + " extended range from line " + extendedRangestartLine + " to " + extendedRangeEndLine + "\n" +
                // "char range: " +extendedRangeStartLineNo+ " to " + extendedRangeEndLineNo + "\n" +
                "exteded  char no " + " from " + extendedNodeRangeStart + " to " +extendedNodeRangeEnd + "\n"+
                "linerange char no " + " from " + lineOuterNodeStart + " to " +lineOuterNodeEnd + "\n" + 
                describeContainerFunction();
    }
}
