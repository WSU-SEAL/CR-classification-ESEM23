package yunogum;

import com.github.gumtreediff.tree.Tree;
//insert and treeinsert do not share interface
public class InsertAction{
    public Tree mappedSrcParent;
    public Tree dstTree;
    public int insertionIndex;
    public int charPosition;
    public InsertAction(Tree mappedSrcParent,Tree dstTree, int insertionIndex, int position) {
        this.mappedSrcParent = mappedSrcParent;
        this.dstTree= dstTree;
        this.insertionIndex = insertionIndex;
        this.charPosition = position;
    }
    
}