package yunogum.MetricCalculator;

import com.github.gumtreediff.tree.Tree;

public  class AstUtils {
    public  static final String IF_STMT = "if_stmt";
    public  static final String SUITE = "suite";
    public  static final String EXPR_STMT = "expr_stmt";
    public  static final String EQUALS = "=";
    public  static final String STRING = "string";
    public  static final String OPERATOR = "operator";
    public  static final String funcdef = "funcdef";

    public static Boolean isTreeType(Tree t, String type){
        return t.getType() != null && t.getType().name.equals(type);
    }

    public static Boolean hasLabel(Tree t, String label){
        return t.getLabel().equals(label);
    }
}
